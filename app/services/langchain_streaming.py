"""普通文本模型流的独立框架入口，逐段交付原始消息片段。

复用消息模板，保留空正文片段中的结束/usage元数据，不缓冲整个HTTP响应。
异常继续交给消费者；消费者保留已交付前缀并判断完成状态，不写数据库或HTTP响应。
"""

from collections.abc import AsyncIterator
from contextlib import aclosing, asynccontextmanager

from httpx import AsyncClient, Client
from langchain_core.messages import AIMessageChunk
from langchain_core.runnables import Runnable
from langchain_deepseek import ChatDeepSeek

from app.config import settings
from app.services.langchain_llm import build_chat_prompt


@asynccontextmanager
async def _open_streaming_chain() -> AsyncIterator[Runnable]:
    """提供模板/模型链，并在正常退出或异常时关闭本次创建的HTTP客户端。"""
    with Client() as sync_http:
        async with AsyncClient() as async_http:
            model = ChatDeepSeek(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                api_base=settings.openai_base_url,
                timeout=60.0,
                max_retries=0,
                cache=False,
                stream_usage=True,
                http_client=sync_http,
                http_async_client=async_http,
            )
            yield build_chat_prompt() | model


async def stream_langchain_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    system_prompt: str = "You are a helpful assistant.",
) -> AsyncIterator[AIMessageChunk]:
    """迭代一次模型流，逐个转交片段，保留结束/usage信息并传播异常。

    函数调用只创建异步生成器，迭代时才打开客户端和请求模型。
    已交付片段不因后续故障撤回；提前停止的调用方应关闭生成器释放资源。
    本入口不声明工具，也不将流结束自动映射为持久化成功。
    """
    async with _open_streaming_chain() as chain:
        async with aclosing(chain.astream({
            "system_prompt": system_prompt,
            "history": history or [],
            "message": message,
        })) as stream:
            async for chunk in stream:
                yield chunk
