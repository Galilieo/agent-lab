"""为网关的一次模型请求记账，发送前和结束后各用一个独立短事务。"""

from collections.abc import Callable, Sequence
from time import monotonic
from uuid import UUID, uuid4

from openai import APIStatusError, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.db.models import ModelCall


async def request_completion(
    session_factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    run_id: UUID,
    *,
    client: AsyncOpenAI,
    purpose: str,
    model: str,
    messages: Sequence[ChatCompletionMessageParam],
    validate: Callable[[ChatCompletion], None] | None = None,
) -> ChatCompletion:
    """发送一次请求并返回已校验的响应；上游或校验异常继续交给调用方。

    调用前需提交所属运行。每次重试重新进入本函数，SDK 不自行重试。
    在响应到达前退出时，已提交的 unknown 行仍能区分未知用量与零用量。
    """
    call_id = uuid4()
    async with session_factory.begin() as session:
        session.add(
            ModelCall(
                call_id=call_id,
                user_id=user_id,
                run_id=run_id,
                purpose=purpose,
                model=model,
                outcome="unknown",
            )
        )

    started = monotonic()
    outcome = "unknown"
    prompt_tokens = completion_tokens = None
    try:
        response = await client.with_options(max_retries=0).chat.completions.create(
            model=model,
            messages=messages,
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
