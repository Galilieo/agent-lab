"""模型网关：业务代码调用模型的唯一入口。

request_completion 负责一次逻辑请求：有限重试上游临时错误、JSON 校验失败时修复一次。
其中每次实际发送都先扣减运行额度，再在 model_call 表登记一行；
登记和结算各用一个独立短事务，业务事务回滚也不会丢失调用记录。
同时提供不可信文本的数据区块包装，并在每次外发前统一遮蔽联系方式和证件号。
"""

import re
from asyncio import sleep
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from json import dumps
from time import monotonic
from typing import Any, cast
from uuid import UUID, uuid4

from openai import APIConnectionError, APIStatusError, AsyncOpenAI, omit
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.config import ModelSettings, settings
from jobpilot.db.models import CallOutcome, ModelCall
from jobpilot.services.prompts import Prompt, load_prompt

_DATA_LABEL_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
# 只匹配 untrusted_data 标签的开头，放过 List<String> 这类正常尖括号。
_DATA_TAG_PATTERN = re.compile(r"<(\s*/?\s*untrusted_data)\b", re.IGNORECASE)

_ID_CARD_PATTERN = re.compile(
    r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
    r"\d{3}[\dXx](?![\dXx])"
)
# 不用 \w 做边界：Python 3 中 \w 会匹配中文，导致「邮箱a@b.com」漏匹配。
_EMAIL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"(?![A-Za-z0-9.-])"
)
_MOBILE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?86[\s-]?)?1[3-9]\d[\s-]?\d{4}[\s-]?\d{4}(?!\d)"
)
# 座机必须带区号和连字符，避免误伤「2025-2026」这类年份区间。
_LANDLINE_PATTERN = re.compile(r"(?<!\d)0\d{2,3}-\d{7,8}(?!\d)")

# 身份证号先于手机号替换，避免 18 位号码中的 11 位子串被误拆。
_PII_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (_ID_CARD_PATTERN, "[ID_CARD]"),
    (_EMAIL_PATTERN, "[EMAIL]"),
    (_MOBILE_PATTERN, "[PHONE]"),
    (_LANDLINE_PATTERN, "[PHONE]"),
)


def wrap_untrusted_text(label: str, text: str) -> str:
    """把不可信文本包进数据区块，并转义正文中伪造的区块标签。

    label 只允许字母、数字、下划线和连字符，防止破坏属性引号。
    """
    if not _DATA_LABEL_PATTERN.fullmatch(label):
        raise ValueError(f"非法的不可信数据区块标签: {label!r}")
    escaped = _DATA_TAG_PATTERN.sub(r"&lt;\1", text)
    return f'<untrusted_data label="{label}">\n{escaped}\n</untrusted_data>'


def redact_pii(text: str) -> str:
    """用占位符遮蔽文本中的身份证号、邮箱、手机号和座机号。"""
    for pattern, placeholder in _PII_RULES:
        text = pattern.sub(placeholder, text)
    return text


class BudgetExhaustedError(RuntimeError):
    """剩余额度不足以发送下一次模型请求。"""


@dataclass
class ModelBudget:
    """保存同一次业务运行共享的剩余调用次数和 token 额度。"""

    remaining_calls: int
    remaining_tokens: int

    def reserve(self, estimated_tokens: int) -> None:
        """检查两项额度，通过后一起扣减。"""
        if self.remaining_calls < 1:
            raise BudgetExhaustedError("模型调用次数已用完")
        if estimated_tokens > self.remaining_tokens:
            raise BudgetExhaustedError("模型 token 额度不足")

        self.remaining_calls -= 1
        self.remaining_tokens -= estimated_tokens


async def request_completion(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    run_id: UUID,
    *,
    client: AsyncOpenAI,
    purpose: str,
    prompt_version: str,
    messages: Sequence[ChatCompletionMessageParam],
    json_output: bool,
    budget: ModelBudget,
    validate: Callable[[ChatCompletion], None] | None = None,
) -> ChatCompletion:
    """完成一次逻辑请求，返回通过 validate 的响应。

    失败时按错误种类处理（规则见 02 第 7 节「重试」「记录」）：
    - 超时、连接错误、5xx：等待后原样重发，总发送次数不超过 model_max_attempts。
    - JSON 输出未通过 Pydantic 校验：附上错误类型重发一次，不占上面的次数。
    - 4xx（含 429）、额度不足、其他异常：直接抛给调用方。
    每次重发都重新扣额度、另记一行 model_call。
    prompt_version 写入每行调用记录；修复重发时追加修复提示词的版本。
    json_output 与提示词和 validate 绑定，由调用方声明，不允许被环境变量改写。
    调用前需已提交所属 ai_run。
    """
    request_messages = list(messages)
    call_prompt_version = prompt_version
    upstream_attempts = 1
    repair_used = False

    while True:
        try:
            return await _send_once(
                session_factory,
                user_id,
                run_id,
                client=client,
                purpose=purpose,
                prompt_version=call_prompt_version,
                messages=request_messages,
                json_output=json_output,
                budget=budget,
                validate=validate,
            )

        except ValidationError as error:
            if not json_output or repair_used:
                raise

            repair_used = True
            repair_prompt = load_prompt("repair_json")
            request_messages.append(_repair_message(error, repair_prompt))
            call_prompt_version = f"{prompt_version}+{repair_prompt.label}"

        except (APIStatusError, APIConnectionError) as error:
            if not _is_retryable(error):
                raise
            if upstream_attempts >= settings.model_max_attempts:
                raise
            upstream_attempts += 1
            await sleep(settings.model_retry_delay_seconds)


def _is_retryable(error: APIStatusError | APIConnectionError) -> bool:
    """超时、连接错误和 5xx 可能是上游临时故障，重发有机会成功。

    APITimeoutError 是 APIConnectionError 的子类，这里一并处理。
    4xx 说明请求本身有问题，重发也不会变好。
    """
    if isinstance(error, APIConnectionError):
        return True
    return 500 <= error.status_code < 600


def _repair_message(
    error: ValidationError, repair_prompt: Prompt
) -> ChatCompletionMessageParam:
    """生成修复请求：只告诉模型错误类型，不回传原始输入和校验详情。"""
    issues = error.errors(include_input=False, include_context=False, include_url=False)
    error_types = ",".join(sorted({issue["type"] for issue in issues}))
    content = repair_prompt.text.format(error_types=error_types)
    return {"role": "user", "content": content}


async def _send_once(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    run_id: UUID,
    *,
    client: AsyncOpenAI,
    purpose: str,
    prompt_version: str,
    messages: Sequence[ChatCompletionMessageParam],
    json_output: bool,
    budget: ModelBudget,
    validate: Callable[[ChatCompletion], None] | None,
) -> ChatCompletion:
    """实际发送一次：查配置并脱敏 → 扣额度 → 登记 unknown → 发送并校验 → 结算。

    这里是所有用途、首次发送与重发通往上游的唯一入口，脱敏放在这里不会漏。
    用途未知或额度不足时在登记前抛出，不会留下调用记录。
    上游错误和校验错误在结算后原样抛出，由 request_completion 决定是否重发。
    """
    model_settings = settings.model_for_purpose(purpose)
    sanitized_messages = _sanitize_messages(messages)
    budget.reserve(_estimate_tokens(sanitized_messages, model_settings.max_tokens))
    call_id = await _register_call(
        session_factory,
        user_id,
        run_id,
        purpose,
        prompt_version,
        model_settings.model_name,
    )

    started = monotonic()
    # 超时、连接错误时 outcome 保持 unknown：请求可能已被上游处理并计费，
    # 但我们拿不到用量，不能记成 0。
    outcome = CallOutcome.UNKNOWN
    usage: CompletionUsage | None = None
    try:
        response = await _create_completion(
            client, model_settings, sanitized_messages, json_output
        )
        usage = response.usage
        # 先记为 invalid_output：validate 抛出任何异常都按校验失败结算。
        outcome = CallOutcome.INVALID_OUTPUT
        if validate is not None:
            validate(response)
        outcome = CallOutcome.SUCCESS
        return response
    except APIStatusError:
        outcome = CallOutcome.HTTP_ERROR
        raise
    finally:
        # 进程被杀时 finally 可能不执行，登记行仍保留 unknown 和空用量。
        latency_ms = int((monotonic() - started) * 1000)
        await _settle_call(session_factory, call_id, outcome, latency_ms, usage)


def _sanitize_messages(
    messages: Sequence[ChatCompletionMessageParam],
) -> list[ChatCompletionMessageParam]:
    """返回脱敏后的消息副本，不改动调用方传入的列表和字典。"""
    return [_sanitize_message(message) for message in messages]


def _sanitize_message(
    message: ChatCompletionMessageParam,
) -> ChatCompletionMessageParam:
    """复制单条消息并遮蔽其中的文本，兼容字符串和分段 content 两种形式。"""
    copied: dict[str, Any] = dict(message)
    content = copied.get("content")
    if isinstance(content, str):
        copied["content"] = redact_pii(content)
    elif isinstance(content, list):
        copied["content"] = [_sanitize_part(part) for part in content]
    return cast(ChatCompletionMessageParam, copied)


def _sanitize_part(part: Any) -> Any:
    """分段 content 中只有 type 为 text 的段落有文本，其余（如图片）原样复制。"""
    if not isinstance(part, dict):
        return part
    copied = dict(part)
    if copied.get("type") == "text" and isinstance(copied.get("text"), str):
        copied["text"] = redact_pii(copied["text"])
    return copied


def _estimate_tokens(
    messages: Sequence[ChatCompletionMessageParam], max_output_tokens: int
) -> int:
    """估算一次发送最多消耗的 token，用于发送前扣额度。

    手头没有 DeepSeek 的分词器，输入部分用序列化后的 UTF-8 字节数代替：
    一个 token 至少对应一个字节，所以字节数只会多估、不会少估。
    输出部分按 max_tokens 上限计算。
    """
    serialized = dumps(list(messages), ensure_ascii=False)
    return len(serialized.encode("utf-8")) + max_output_tokens


async def _create_completion(
    client: AsyncOpenAI,
    model_settings: ModelSettings,
    messages: Sequence[ChatCompletionMessageParam],
    json_output: bool,
) -> ChatCompletion:
    """按用途配置组装参数并发送；关闭 SDK 自带重试，重试只由网关负责。"""
    return await client.with_options(max_retries=0).chat.completions.create(
        model=model_settings.model_name,
        messages=messages,
        max_tokens=model_settings.max_tokens,
        # DeepSeek 思考模式下 temperature 不生效，干脆不传。
        temperature=omit if model_settings.thinking else model_settings.temperature,
        response_format={"type": "json_object"} if json_output else omit,
        extra_body={
            "thinking": {"type": "enabled" if model_settings.thinking else "disabled"}
        },
    )


async def _register_call(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    run_id: UUID,
    purpose: str,
    prompt_version: str,
    model_name: str,
) -> UUID:
    """发送前用独立事务登记一行 unknown，返回供结算使用的 call_id。"""
    call_id = uuid4()
    async with session_factory.begin() as session:
        session.add(
            ModelCall(
                call_id=call_id,
                user_id=user_id,
                run_id=run_id,
                purpose=purpose,
                prompt_version=prompt_version,
                model=model_name,
                outcome=CallOutcome.UNKNOWN,
            )
        )
    return call_id


async def _settle_call(
    session_factory: async_sessionmaker[AsyncSession],
    call_id: UUID,
    outcome: CallOutcome,
    latency_ms: int,
    usage: CompletionUsage | None,
) -> None:
    """用另一个独立事务回填结果、耗时和用量；没收到响应时用量留空。"""
    async with session_factory.begin() as session:
        await session.execute(
            update(ModelCall)
            .where(ModelCall.call_id == call_id)
            .values(
                outcome=outcome,
                latency_ms=latency_ms,
                prompt_tokens=usage.prompt_tokens if usage else None,
                completion_tokens=usage.completion_tokens if usage else None,
            )
        )
