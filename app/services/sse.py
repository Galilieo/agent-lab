"""将普通文本模型片段编码为应用SSE事件，供后续HTTP响应消费。

本层不创建模型请求、不写数据库。done只表示输入模型流正常完整，
不表示业务回答已保存；连接取消和未知异常继续向调用方传播。
"""

import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import aclosing

from langchain_core.messages import AIMessageChunk
from openai import APIError, APITimeoutError


class InvalidStreamError(Exception):
    """普通文本流缺少正常结束、有效正文或出现不支持的输出形状。"""


def encode_sse(event_name: str, data: dict) -> str:
    """编码一个完整应用事件；JSON转义正文换行，避免破坏事件边界。"""
    if event_name not in {"delta", "done", "error"}:
        raise ValueError("Unsupported SSE event name.")
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False)
    return f"event: {event_name}\ndata: {payload}\n\n"


def stream_error_payload(error: APIError | InvalidStreamError) -> dict[str, str]:
    """为已知模型/流协议错误提供稳定负载，不向客户端转发原始异常正文。"""
    if isinstance(error, APITimeoutError):
        return {"code": "model_timeout", "message": "模型响应超时。"}
    if isinstance(error, InvalidStreamError):
        return {"code": "invalid_model_stream", "message": "模型未正常完成文本回答。"}
    return {"code": "model_request_failed", "message": "模型请求失败。"}


async def stream_sse_events(
    chunks: AsyncGenerator[AIMessageChunk, None],
) -> AsyncIterator[str]:
    """逐块发送正文，保留结束与usage，正常收尾或已知错误只发一种终态。

    本层接管输入生成器的关闭；正常、异常或调用方显式关闭时释放上游。
    只支持无工具的普通文本且finish_reason为stop；未知异常不冒充模型失败。
    """
    combind = None

    try:
        async with aclosing(chunks) as stream:
            async for chunk in stream:
                if (
                    not isinstance(chunk.content, str)
                    or chunk.tool_calls
                    or chunk.invalid_tool_calls
                ):
                    raise InvalidStreamError()

                combind = chunk if combind is None else combind + chunk

                if chunk.content:
                    yield encode_sse("delta", {"text": chunk.content})
        if (
            combind is None
            or not combind.content.strip()
            or combind.response_metadata.get("finish_reason") != "stop"
        ):
            raise InvalidStreamError()
    except (APIError, InvalidStreamError) as exc:
        yield encode_sse("error", stream_error_payload(exc))
        return

    yield encode_sse("done", {
        "finish_reason": "stop",
        "usage": combind.usage_metadata,
    })
