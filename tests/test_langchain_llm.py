"""验证 LangChain 调用入口的消息组装与框架返回对象。

真实执行 ChatDeepSeek、底层 SDK 的请求序列化和响应解析；
仅用 httpx.MockTransport 替代外部 HTTP，不读取真实 .env 或调用模型。
"""

import asyncio
import json

import httpx
from langchain_core.messages import AIMessage
from langchain_deepseek import ChatDeepSeek

from app.services import langchain_llm


def test_langchain_reply_preserves_message_order_and_returns_ai_message(
    monkeypatch,
) -> None:
    """历史与当前问题按序且各出现一次，返回正文及框架标准化 usage。"""
    observed = []
    history = [
        {"role": "user", "content": "我叫小宇"},
        {"role": "assistant", "content": "记住了"},
    ]

    # 仅覆盖本测试的进程配置；占位地址及 Key 不来自真实 .env。
    monkeypatch.setattr(langchain_llm.settings, "openai_api_key", "offline-placeholder")
    monkeypatch.setattr(
        langchain_llm.settings, "openai_base_url", "https://example.invalid/v1"
    )
    monkeypatch.setattr(langchain_llm.settings, "openai_model", "deepseek-learning")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")

    def respond(request: httpx.Request) -> httpx.Response:
        observed.append({
            "method": request.method,
            "url": str(request.url),
            "payload": json.loads(request.content),
        })
        return httpx.Response(
            200,
            json={
                "id": "offline-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "deepseek-learning",
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "你叫小宇。"},
                }],
                "usage": {
                    "prompt_tokens": 8,
                    "completion_tokens": 4,
                    "total_tokens": 12,
                },
            },
        )

    async def run_scenario() -> AIMessage:
        with httpx.Client(transport=httpx.MockTransport(respond)) as sync_http:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as async_http:
                def create_model(**kwargs):
                    # 保留真实模型类，仅为 SDK 注入离线 HTTP 客户端。
                    return ChatDeepSeek(
                        **kwargs,
                        http_client=sync_http,
                        http_async_client=async_http,
                    )

                monkeypatch.setattr(langchain_llm, "ChatDeepSeek", create_model)
                return await langchain_llm.generate_langchain_reply(
                    "我叫什么？",
                    history,
                    system_prompt="请简洁回答。",
                )

    result = asyncio.run(run_scenario())

    assert len(observed) == 1
    assert observed[0]["method"] == "POST"
    assert observed[0]["url"] == "https://example.invalid/v1/chat/completions"
    assert observed[0]["payload"]["model"] == "deepseek-learning"
    assert observed[0]["payload"]["messages"] == [
        {"role": "system", "content": "请简洁回答。"},
        {"role": "user", "content": "我叫小宇"},
        {"role": "assistant", "content": "记住了"},
        {"role": "user", "content": "我叫什么？"},
    ]
    assert history == [
        {"role": "user", "content": "我叫小宇"},
        {"role": "assistant", "content": "记住了"},
    ]
    assert isinstance(result, AIMessage)
    assert result.content == "你叫小宇。"
    assert result.tool_calls == []
    assert result.usage_metadata["input_tokens"] == 8
    assert result.usage_metadata["output_tokens"] == 4
    assert result.usage_metadata["total_tokens"] == 12
