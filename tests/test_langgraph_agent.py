"""真实LangGraph、框架模型适配和计算器，外部模型HTTP使用预设响应。

验证条件分支、工具循环、执行前预算与部分失败记录，不证明真实模型工具选择。
"""

import asyncio
import json

import httpx
import pytest

from app.services import langchain_adapter, langgraph_agent
from app.services.agent import (
    AgentModelCallLimitError,
    AgentResult,
    AgentRunError,
    AgentToolError,
)
from app.services.llm import LLMTimeoutError


@pytest.fixture
def offline_graph(monkeypatch):
    """只替换HTTP传输，工具入口用观察包装保留真实执行与校验。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(langchain_adapter.settings, "openai_api_key", "offline-placeholder")
    monkeypatch.setattr(langchain_adapter.settings, "openai_base_url", "https://example.invalid/v1")
    monkeypatch.setattr(langchain_adapter.settings, "openai_model", "offline-model")
    observed = {"requests": [], "tool_attempts": []}
    real_execute = langgraph_agent.execute_tool

    def observed_execute(call):
        observed["tool_attempts"].append(call.call_id)
        return real_execute(call)

    monkeypatch.setattr(langgraph_agent, "execute_tool", observed_execute)

    def prepare(messages):
        pending = iter(messages)

        def respond(request):
            observed["requests"].append(json.loads(request.content))
            message = next(pending)
            if message == "timeout":
                raise httpx.ReadTimeout("offline timeout", request=request)
            return httpx.Response(200, json={
                "id": "offline-graph", "object": "chat.completion", "created": 0,
                "model": "offline-model",
                "choices": [{
                    "index": 0,
                    "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                    "message": message,
                }],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
            })

        def create_client(**kwargs):
            return httpx.AsyncClient(**kwargs, transport=httpx.MockTransport(respond))

        monkeypatch.setattr(langchain_adapter, "AsyncClient", create_client)

    return prepare, observed


def calculator_request(arguments='{"left":2,"operator":"+","right":3}'):
    """预设模型请求，参数字符串原样经过模型适配再交工具校验。"""
    return {
        "role": "assistant", "content": None,
        "tool_calls": [{
            "id": "call_graph", "type": "function",
            "function": {"name": "calculator", "arguments": arguments},
        }],
    }


@pytest.mark.parametrize("use_tool", [False, True], ids=["direct", "calculator"])
def test_graph_routes_to_end_or_calculator_and_preserves_calls(offline_graph, use_tool):
    """同图直接结束或真实计算后回模型；每个节点只提交新增调用/消息。"""
    prepare, observed = offline_graph
    responses = [calculator_request()] if use_tool else []
    responses.append({"role": "assistant", "content": "结果是5。"})
    prepare(responses)
    history = [{"role": "assistant", "content": "继续。"}]

    result = asyncio.run(langgraph_agent.run_calculator_graph("计算2+3", history))

    assert isinstance(result, AgentResult)
    assert result.answer == "结果是5。"
    assert len(result.model_calls) == len(observed["requests"]) == (2 if use_tool else 1)
    assert observed["tool_attempts"] == (["call_graph"] if use_tool else [])
    for call, payload in zip(result.model_calls, observed["requests"]):
        assert call.upstream_status == 200
        assert call.total_tokens == 12
        assert [tool["function"]["name"] for tool in payload["tools"]] == ["calculator"]
        assert payload["messages"][1:3] == [
            {"role": "assistant", "content": "继续。"},
            {"role": "user", "content": "计算2+3"},
        ]
    if use_tool:
        assert result.model_calls[0].tool_calls[0].call_id == "call_graph"
        sent = observed["requests"][1]["messages"]
        assert [message["role"] for message in sent] == ["system", "assistant", "user", "assistant", "tool"]
        assert sent[-2]["tool_calls"][0]["id"] == "call_graph"
        assert sent[-1] == {"role": "tool", "tool_call_id": "call_graph", "content": "5"}
    assert history == [{"role": "assistant", "content": "继续。"}]


@pytest.mark.parametrize("failure", ["timeout", "bad-arguments", "budget"])
def test_graph_preserves_calls_and_checks_budget_before_tools(offline_graph, failure):
    """模型失败/工具失败保留已发生调用；最后一次模型预算后不执行工具。"""
    prepare, observed = offline_graph
    if failure == "timeout":
        messages = [calculator_request(), "timeout"]
        expected = AgentRunError
    elif failure == "bad-arguments":
        messages = [calculator_request("{bad json")]
        expected = AgentToolError
    else:
        messages = [calculator_request()]
        expected = AgentModelCallLimitError
    prepare(messages)

    with pytest.raises(expected) as caught:
        asyncio.run(langgraph_agent.run_calculator_graph(
            "计算2+3", max_model_calls=1 if failure == "budget" else 3,
        ))

    assert len(caught.value.completed_model_calls) == 1
    completed = caught.value.completed_model_calls[0]
    assert completed.upstream_status == 200
    assert completed.total_tokens == 12
    assert completed.tool_calls[0].call_id == "call_graph"
    if failure == "timeout":
        assert len(observed["requests"]) == 2
        assert observed["tool_attempts"] == ["call_graph"]
        assert isinstance(caught.value.cause, LLMTimeoutError)
    elif failure == "bad-arguments":
        assert len(observed["requests"]) == 1
        assert observed["tool_attempts"] == ["call_graph"]
        assert isinstance(caught.value.cause, json.JSONDecodeError)
    else:
        assert len(observed["requests"]) == 1
        assert observed["tool_attempts"] == []
