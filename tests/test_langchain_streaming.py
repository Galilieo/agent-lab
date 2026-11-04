"""真实SDK解析离线SSE字节流，检查及时转发、元数据和失败前缀。

HTTP状态为200后可继续出现读取故障；不调用真实模型，也不验证浏览器SSE接口。
"""

import asyncio
import json

import httpx
import pytest
from langchain_core.messages import AIMessageChunk
from openai import APITimeoutError

from app.services import langchain_streaming


def event(delta=None, *, finish_reason=None, usage=None):
    """编码上游Chat Completions的SSE事件，delta和usage仍由真实SDK解析。"""
    data = {
        "id": "offline-stream", "object": "chat.completion.chunk", "created": 0,
        "model": "offline-model",
        "choices": [] if usage else [{"index": 0, "delta": delta or {}, "finish_reason": finish_reason}],
    }
    if usage:
        data["usage"] = usage
    return ("data: " + json.dumps(data, ensure_ascii=False) + "\n\n").encode("utf-8")


@pytest.fixture
def offline_stream(monkeypatch):
    """将客户端连接到按需产出字节的流；记录终止事件与资源关闭。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(langchain_streaming.settings, "openai_api_key", "offline-placeholder")
    monkeypatch.setattr(langchain_streaming.settings, "openai_base_url", "https://example.invalid/v1")
    monkeypatch.setattr(langchain_streaming.settings, "openai_model", "offline-model")
    state = {"requests": [], "finish_sent": False, "closed": False}

    def prepare(*, fail=False):
        class EventStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield event({"role": "assistant", "content": ""})
                yield event({"content": "计算结果是"})
                if fail:
                    raise httpx.ReadTimeout("offline stream interrupted")
                yield event({"content": "437"})
                state["finish_sent"] = True
                yield event(finish_reason="stop")
                yield event(usage={"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12})
                yield b"data: [DONE]\n\n"

            async def aclose(self):
                state["closed"] = True

        def respond(request):
            state["requests"].append(json.loads(request.content))
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=EventStream(),
            )

        def create_client(**kwargs):
            return httpx.AsyncClient(**kwargs, transport=httpx.MockTransport(respond))

        monkeypatch.setattr(langchain_streaming, "AsyncClient", create_client)

    return prepare, state


def test_stream_delivers_before_finish_and_preserves_usage(offline_stream):
    """一次请求的正文在结束前可见，原始空片段/usage被保留且客户端关闭。"""
    prepare, state = offline_stream
    prepare()
    history = [{"role": "assistant", "content": "继续。"}]
    received = []

    async def consume():
        stream = langchain_streaming.stream_langchain_reply(
            "计算23乘19", history, system_prompt="请简洁回答。",
        )
        assert state["requests"] == []
        async for chunk in stream:
            if chunk.content and not any(item.content for item in received):
                assert state["finish_sent"] is False
            received.append(chunk)

    asyncio.run(consume())

    assert all(isinstance(chunk, AIMessageChunk) for chunk in received)
    combined = received[0]
    for chunk in received[1:]:
        combined = combined + chunk
    assert combined.content == "计算结果是437"
    assert combined.response_metadata["finish_reason"] == "stop"
    assert combined.usage_metadata["total_tokens"] == 12
    assert any(chunk.content == "" and chunk.usage_metadata for chunk in received)
    assert len(state["requests"]) == 1
    payload = state["requests"][0]
    assert payload["stream"] is True
    assert payload["stream_options"] == {"include_usage": True}
    assert payload["messages"] == [
        {"role": "system", "content": "请简洁回答。"},
        {"role": "assistant", "content": "继续。"},
        {"role": "user", "content": "计算23乘19"},
    ]
    assert history == [{"role": "assistant", "content": "继续。"}]
    assert state["closed"] is True


def test_stream_propagates_timeout_after_delivering_prefix(offline_stream):
    """HTTP200后读取超时仍是失败，消费者已有前缀保留，不虚构最终usage。"""
    prepare, state = offline_stream
    prepare(fail=True)
    received = []

    async def consume():
        async for chunk in langchain_streaming.stream_langchain_reply("计算23乘19"):
            received.append(chunk)

    with pytest.raises(APITimeoutError):
        asyncio.run(consume())

    assert "".join(chunk.content for chunk in received) == "计算结果是"
    assert all(chunk.usage_metadata is None for chunk in received)
    assert len(state["requests"]) == 1
    assert state["finish_sent"] is False
    assert state["closed"] is True
