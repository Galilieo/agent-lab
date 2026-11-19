"""为网关的一次模型请求记账，发送前和结束后各用一个独立短事务。"""

from collections.abc import Callable, Sequence
from time import monotonic
from uuid import UUID, uuid4

from openai import APIStatusError, AsyncOpenAI, omit
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.config import settings
from jobpilot.db.models import ModelCall


async def request_completion(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    run_id: UUID,
    *,
    client: AsyncOpenAI,
    purpose: str,
    messages: Sequence[ChatCompletionMessageParam],
    json_output: bool,
    validate: Callable[[ChatCompletion], None] | None = None,
) -> ChatCompletion:
    """发送一次请求并返回已校验的响应；上游或校验异常继续交给调用方。

    模型与采样参数按用途从配置读取；json_output 与提示词和 validate 绑定，
    由调用方声明，不允许被环境变量改写。
    调用前需提交所属运行。每次重试重新进入本函数，SDK 不自行重试。
    在响应到达前退出时，已提交的 unknown 行仍能区分未知用量与零用量。
    """
    model_settings = settings.model_for_purpose(purpose)
    call_id = uuid4()
    async with session_factory.begin() as session:
        session.add(
            ModelCall(
                call_id=call_id,
                user_id=user_id,
                run_id=run_id,
                purpose=purpose,
                model=model_settings.model_name,
                outcome="unknown",
            )
        )

    started = monotonic()
    outcome = "unknown"
    prompt_tokens = completion_tokens = None
    try:
        response = await client.with_options(max_retries=0).chat.completions.create(
            model=model_settings.model_name,
            messages=messages,
            max_tokens=model_settings.max_tokens,
            temperature=omit if model_settings.thinking else model_settings.temperature,
            response_format={"type": "json_object"} if json_output else omit,
            extra_body={
                "thinking": {
                    "type": "enabled" if model_settings.thinking else "disabled"
                }
            },
        )
        if response.usage is not None:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
        outcome = "invalid_output"
        if validate is not None:
            validate(response)
        outcome = "success"
        return response
    except APIStatusError:
        outcome = "http_error"
        raise
    finally:
        # 进程被杀时 finally 可能不执行，登记行仍保留 unknown 和空用量。
        elapsed_ms = int((monotonic() - started) * 1000)
        async with session_factory.begin() as session:
            await session.execute(
                update(ModelCall)
                .where(ModelCall.call_id == call_id)
                .values(
                    outcome=outcome,
                    latency_ms=elapsed_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            )
