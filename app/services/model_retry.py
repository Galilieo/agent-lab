"""显式调用的非流式模型重试策略；重试调用方绑定的一次模型操作。

不执行工具、重启Agent、写数据库或重新消费已交付的流。
失败尝试只记录安全元数据；不表示已经接入/chat的调用审计。
"""

from asyncio import sleep
from collections.abc import Awaitable, Callable
import logging

from app.services.llm import (
    LLMConnectionError,
    LLMRequestError,
    LLMResult,
    LLMTimeoutError,
    LLMUpstreamError,
)

logger = logging.getLogger(__name__)


async def retry_model_call(
    call: Callable[[], Awaitable[LLMResult]],
    *,
    max_attempts: int = 2,
    delay_seconds: float = 0.5,
) -> LLMResult:
    """有限重试同一个无参异步模型操作，成功返回结果，终止时保留原异常。

    max_attempts包含首次；仅重试超时、连接错误及429/502/503/504。
    每次失败记录尝试序号与分类，不写异常正文；取消不捕获、不重试。
    调用方须绑定相同输入且关闭底层SDK重试；本层不保证供应商计算幂等。
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")
    if delay_seconds < 0:
        raise ValueError("delay_seconds must not be negative.")

    for attempt in range(1, max_attempts + 1):
        try:
            return await call()
        except LLMRequestError as exc:
            retryable = (
                isinstance(exc, (LLMTimeoutError, LLMConnectionError))
                or (
                    isinstance(exc, LLMUpstreamError)
                    and exc.upstream_status in {429, 502, 503, 504}
                )
            )
            will_retry = retryable and attempt < max_attempts

            logger.warning(
                "Model attempt failed attempt=%s max_attempts=%s "
                "model=%s outcome=%s status=%s latency_ms=%.2f retry=%s",
                attempt,
                max_attempts,
                exc.model,
                exc.outcome,
                exc.upstream_status,
                exc.latency_ms,
                will_retry,
            )

            if not will_retry:
                raise

            await sleep(delay_seconds)
