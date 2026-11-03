"""以预设模型 HTTP 响应验证真实框架 Agent 与计算器循环。

保留 create_agent、模型 SDK、工具校验与计算器执行；仅替代外部 HTTP。
不访问真实模型或数据库，不据预设工具请求证明真实模型的选择能力。
"""

import asyncio
import json

import httpx
import pytest
from langchain.agents.middleware.model_call_limit import ModelCallLimitExceededError
from langchain_core.messages import AIMessage, ToolMessage
from langchain_deepseek import ChatDeepSeek
from openai import APITimeoutError

from app.services import langchain_agent
from app.services.langchain_callbacks import ModelCallRecorder


@pytest.fixture
def offline_agent(monkeypatch):
    """提供可编排的上游响应，收集真实SDK请求，客户端随每次场景关闭。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(langchain_agent.settings, "openai_api_key", "offline-placeholder")
    monkeypatch.setattr(
        langchain_agent.settings, "openai_base_url", "https://example.invalid/v1"
    )
    monkeypatch.setattr(langchain_agent.settings, "openai_model", "offline-model")
    observed = []

    async def run(responses, *, history=None, callbacks=None):
        pending = iter(responses)

        def respond(request):
            observed.append(json.loads(request.content))
            message = next(pending)
            if isinstance(message, httpx.RequestError):
                raise message
            return httpx.Response(200, json={
                "id": f"offline-{len(observed)}",
                "object": "chat.completion",
                "created": 0,
                "model": "offline-model",
                "choices": [{
                    "index": 0,
                    "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                    "message": message,
                }],
                "usage": {
                    "prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12,
                },
            })

        with httpx.Client(transport=httpx.MockTransport(respond)) as sync_http:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(respond)
            ) as async_http:
                def create_model(**kwargs):
                    return ChatDeepSeek(
                        **kwargs,
                        http_client=sync_http,
                        http_async_client=async_http,
                    )

                monkeypatch.setattr(langchain_agent, "ChatDeepSeek", create_model)
                return await langchain_agent.run_langchain_agent(
                    "计算2+3", history, callbacks=callbacks
                )

    return run, observed


def calculator_request(call_id):
    """构造上游协议中的工具请求，与框架规范化后的ToolCall形状区分。"""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": call_id,
            "type": "function",
            "function": {
                "name": "calculator",
                "arguments": '{"left":2,"operator":"+","right":3}',
            },
        }],
    }


def test_langchain_agent_returns_tool_result_to_model_and_finishes(offline_agent):
    """模型工具请求后真实计算、按ID回传，第二次模型回复结束循环。"""
    run, observed = offline_agent
    history = [{"role": "user", "content": "请用中文回答。"}]
    messages = asyncio.run(run([
        calculator_request("call_001"),
        {"role": "assistant", "content": "结果是5。"},
    ], history=history))

    assert len(observed) == 2
    assert [tool["function"]["name"] for tool in observed[0]["tools"]] == ["calculator"]
    assert [tool["function"]["name"] for tool in observed[1]["tools"]] == ["calculator"]
    assert [m["role"] for m in observed[1]["messages"]] == [
        "system", "user", "user", "assistant", "tool",
    ]
    assert observed[1]["messages"][-2]["tool_calls"][0]["id"] == "call_001"
    assert observed[1]["messages"][-1] == {
        "role": "tool", "content": "5", "tool_call_id": "call_001",
    }
    assert [m.type for m in messages] == ["human", "human", "ai", "tool", "ai"]
    assert messages[0].content == "请用中文回答。"
    assert messages[1].content == "计算2+3"
    assert isinstance(messages[-2], ToolMessage)
    assert messages[-2].content == "5"
    assert messages[-2].tool_call_id == "call_001"
    assert isinstance(messages[-1], AIMessage)
    assert messages[-1].content == "结果是5。"
    assert messages[-1].tool_calls == []
    assert history == [{"role": "user", "content": "请用中文回答。"}]


def test_langchain_agent_stops_before_fourth_model_call(offline_agent):
    """模型持续请求工具时，三次模型调用后抛限额异常，不生成第四次请求。"""
    run, observed = offline_agent

    with pytest.raises(ModelCallLimitExceededError):
        asyncio.run(run([
            calculator_request("call_001"),
            calculator_request("call_002"),
            calculator_request("call_003"),
        ]))

    assert len(observed) == 3


def test_model_callbacks_record_each_successful_call(offline_agent):
    """真实两次模型调用各留下独立记录，工具执行不额外算成模型调用。"""
    run, observed = offline_agent
    recorder = ModelCallRecorder()

    messages = asyncio.run(run([
        calculator_request("call_001"),
        {"role": "assistant", "content": "结果是5。"},
    ], callbacks=[recorder]))

    assert messages[-1].content == "结果是5。"
    assert len(observed) == 2
    assert [record.outcome for record in recorder.records] == ["succeeded", "succeeded"]
    assert len({record.run_id for record in recorder.records}) == 2
    for record in recorder.records:
        assert record.latency_ms >= 0
        assert record.prompt_tokens == 8
        assert record.completion_tokens == 4
        assert record.total_tokens == 12
        assert record.error_type is None


def test_model_callbacks_preserve_success_and_timeout_when_agent_raises(offline_agent):
    """第二次模型超时时原异常继续抛出，外部记录器保留一次成功及一次失败。"""
    run, observed = offline_agent
    recorder = ModelCallRecorder()

    with pytest.raises(APITimeoutError) as error_info:
        asyncio.run(run([
            calculator_request("call_001"),
            httpx.ReadTimeout("offline-timeout"),
        ], callbacks=[recorder]))

    assert len(observed) == 2
    assert [record.outcome for record in recorder.records] == ["succeeded", "failed"]
    assert recorder.records[0].total_tokens == 12
    assert recorder.records[1].latency_ms >= 0
    assert recorder.records[1].total_tokens is None
    assert recorder.records[1].error_type == type(error_info.value).__name__
