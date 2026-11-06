"""真实SDK解析离线SSE字节流，检查及时转发、元数据和失败前缀。

HTTP状态为200后可继续出现读取故障；同时验证应用事件编码/模型流转换。
同时用TestClient验证本应用/stream契约；不调用真实模型或验证浏览器及时显示。
"""

import asyncio
import json
from contextlib import aclosing

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk
from openai import APITimeoutError

from app.services import langchain_streaming, sse
from app.main import app


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
    state = {
        "requests": [], "finish_sent": False, "closed": False,
        "waiting": asyncio.Event(), "cancelled": False,
    }

    def prepare(*, fail=False, include_finish=True, wait_after_first=False):
        class EventStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield event({"role": "assistant", "content": ""})
                yield event({"content": "计算结果是"})
                if wait_after_first:
                    state["waiting"].set()
                    try:
                        await asyncio.Event().wait()
                    except asyncio.CancelledError:
                        state["cancelled"] = True
                        raise
                if fail:
                    raise httpx.ReadTimeout("offline stream interrupted")
                yield event({"content": "437"})
                if include_finish:
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


def test_sse_encoder_keeps_multiline_text_inside_one_event():
    """JSON还原中文及换行；正文中的event字样不能伪造另一条SSE事件。"""
    text = '第一行\n\nevent: done\n含有"引号"的第二行'
    frame = sse.encode_sse("delta", {"text": text})

    event_line, data_line, ending = frame.split("\n", 2)
    assert event_line == "event: delta"
    assert data_line.startswith("data: ")
    assert json.loads(data_line.removeprefix("data: ")) == {"text": text}
    assert ending == "\n"


@pytest.mark.parametrize("case", ["normal", "timeout", "missing-finish"])
def test_model_stream_becomes_incremental_sse_with_one_terminal_event(offline_stream, case):
    """正常流发done；超时或缺失结束标记发error，已交付正文保留且关闭上游。"""
    prepare, state = offline_stream
    prepare(fail=case == "timeout", include_finish=case != "missing-finish")
    received = []

    async def consume():
        source = langchain_streaming.stream_langchain_reply("计算23乘19")
        assert state["requests"] == []
        async for frame in sse.stream_sse_events(source):
            # 转换器每次交出完整编码帧；这里不模拟网络拆包或实现浏览器解析器。
            event_line, data_line, ending = frame.split("\n", 2)
            assert ending == "\n"
            event_name = event_line.removeprefix("event: ")
            payload = json.loads(data_line.removeprefix("data: "))
            if event_name == "delta":
                assert state["finish_sent"] is False
            received.append((event_name, payload))

    asyncio.run(consume())

    expected_text = "计算结果是" if case == "timeout" else "计算结果是437"
    assert "".join(data["text"] for name, data in received if name == "delta") == expected_text
    assert [name for name, _ in received[:-1]] == (["delta"] if case == "timeout" else ["delta", "delta"])
    if case == "normal":
        assert received[-1][0] == "done"
        assert received[-1][1]["finish_reason"] == "stop"
        usage = received[-1][1]["usage"]
        assert {key: usage[key] for key in ("input_tokens", "output_tokens", "total_tokens")} == {
            "input_tokens": 8, "output_tokens": 4, "total_tokens": 12,
        }
    elif case == "timeout":
        assert received[-1] == ("error", {
            "code": "model_timeout", "message": "模型响应超时。",
        })
    else:
        assert received[-1] == ("error", {
            "code": "invalid_model_stream", "message": "模型未正常完成文本回答。",
        })
    assert len(state["requests"]) == 1
    assert state["closed"] is True


@pytest.mark.parametrize("fail", [False, True], ids=["normal", "timeout"])
def test_text_stream_http_returns_sse_with_success_or_error(offline_stream, fail):
    """HTTP200响应体含应用事件；中途超时以error结束，验证实际路由和SDK链路。"""
    prepare, state = offline_stream
    prepare(fail=fail)
    # 本路由不依赖数据库；不启用lifespan，不触碰运行者配置的业务数据库。
    client = TestClient(app)
    try:
        response = client.post("/stream", json={"message": "计算23乘19"})
    finally:
        client.close()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    frames = response.text.split("\n\n")
    assert frames.pop() == ""
    received = []
    for frame in frames:
        event_line, data_line = frame.split("\n", 1)
        received.append((
            event_line.removeprefix("event: "),
            json.loads(data_line.removeprefix("data: ")),
        ))
    assert [name for name, _ in received] == (
        ["delta", "error"] if fail else ["delta", "delta", "done"]
    )
    assert "".join(data["text"] for name, data in received if name == "delta") == (
        "计算结果是" if fail else "计算结果是437"
    )
    if fail:
        assert received[-1][1]["code"] == "model_timeout"
    else:
        assert received[-1][1]["finish_reason"] == "stop"
        assert received[-1][1]["usage"]["total_tokens"] == 12
    assert len(state["requests"]) == 1
    assert state["requests"][0]["messages"][-1] == {
        "role": "user", "content": "计算23乘19",
    }
    assert state["closed"] is True


def test_text_stream_http_rejects_empty_message_before_model(offline_stream):
    """空输入在响应开始前由请求模型拒绝，返回JSON422且零模型请求。"""
    prepare, state = offline_stream
    prepare()
    client = TestClient(app)
    try:
        response = client.post("/stream", json={"message": ""})
    finally:
        client.close()

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/json")
    assert state["requests"] == []


def test_cancelled_stream_propagates_cancellation_and_closes_upstream(offline_stream):
    """首段后取消待读取任务，真实SDK清理上游；取消不转换为应用错误或成功事件。"""
    prepare, state = offline_stream
    prepare(wait_after_first=True)

    async def consume():
        source = langchain_streaming.stream_langchain_reply("计算23乘19")
        async with aclosing(sse.stream_sse_events(source)) as events:
            first = await asyncio.wait_for(anext(events), timeout=3)
            assert first.startswith("event: delta\n")
            pending = asyncio.create_task(anext(events))
            try:
                await asyncio.wait_for(state["waiting"].wait(), timeout=3)
            finally:
                pending.cancel()
                # 若取消被错误地转换为error/done，这里不会抛CancelledError，测试失败。
                with pytest.raises(asyncio.CancelledError):
                    await pending

        assert state["cancelled"] is True
        assert state["finish_sent"] is False
        assert state["closed"] is True
        assert len(state["requests"]) == 1

    asyncio.run(consume())
