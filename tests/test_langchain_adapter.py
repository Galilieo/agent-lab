"""运行真实模板/ChatDeepSeek/SDK，以假HTTP验证模型、工具及Agent组合契约。

HTTP钩子保持真实执行，不直接伪造AIMessage或SDK异常；不访问模型服务。
"""

import asyncio
from copy import deepcopy
import json

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError

from app.services import agent, langchain_adapter
from app.services.llm import (
    LLMConnectionError,
    LLMResponseError,
    LLMResult,
    LLMTimeoutError,
    LLMUpstreamError,
)
from app.tools import CALCULATOR_TOOL, execute_tool


@pytest.fixture
def offline_call(monkeypatch):
    """只替换适配模块的客户端工厂，保留调用方配置的响应钩子。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(langchain_adapter.settings, "openai_api_key", "offline-placeholder")
    monkeypatch.setattr(
        langchain_adapter.settings, "openai_base_url", "https://example.invalid/v1"
    )
    monkeypatch.setattr(langchain_adapter.settings, "openai_model", "offline-model")
    observed = []

    def prepare(scenario, *, messages=None):
        pending = iter(messages) if messages is not None else None

        def respond(request):
            observed.append(json.loads(request.content))
            if scenario == "timeout":
                raise httpx.ReadTimeout("offline timeout", request=request)
            if scenario == "connection":
                raise httpx.ConnectError("offline connection error", request=request)
            if scenario == "upstream":
                return httpx.Response(429, json={"error": {"message": "offline limit"}})
            if scenario == "invalid":
                return httpx.Response(200, json={
                    "id": "offline-invalid", "object": "chat.completion", "created": 0,
                    "model": "offline-model", "choices": None,
                })
            if pending is not None:
                message = next(pending)
                if isinstance(message, httpx.RequestError):
                    raise message
                return httpx.Response(200, json={
                    "id": "offline-tool", "object": "chat.completion", "created": 0,
                    "model": "offline-model",
                    "choices": [{
                        "index": 0,
                        "finish_reason": "tool_calls" if message.get("tool_calls") else "stop",
                        "message": message,
                    }],
                    "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
                })
            # 使用201验证状态来自真实响应钩子，不能把所有成功响应写死成200。
            return httpx.Response(201, json={
                "id": "offline-success", "object": "chat.completion", "created": 0,
                "model": "offline-model",
                "choices": [{
                    "index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "你好。"},
                }],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
            })

        def create_client(**kwargs):
            return httpx.AsyncClient(
                **kwargs, transport=httpx.MockTransport(respond),
            )

        # 修改本模块导入的别名，不修改httpx.AsyncClient类本身。
        monkeypatch.setattr(langchain_adapter, "AsyncClient", create_client)

    return prepare, observed


def test_plain_call_returns_project_result_with_observed_status(offline_call):
    """SDK消息经适配变成项目结果，保留实际状态、Token及输入消息。"""
    prepare, observed = offline_call
    prepare("success")
    history = [{"role": "assistant", "content": "继续。"}]

    result = asyncio.run(langchain_adapter.generate_langchain_result(
        "你好", history, system_prompt="请简洁回答。",
    ))

    assert len(observed) == 1
    assert observed[0]["messages"] == [
        {"role": "system", "content": "请简洁回答。"},
        {"role": "assistant", "content": "继续。"},
        {"role": "user", "content": "你好"},
    ]
    assert isinstance(result, LLMResult)
    assert result.answer == "你好。"
    assert result.model == "offline-model"
    assert result.upstream_status == 201
    assert result.latency_ms >= 0
    assert (result.prompt_tokens, result.completion_tokens, result.total_tokens) == (8, 4, 12)
    assert result.tool_calls == []
    assert history == [{"role": "assistant", "content": "继续。"}]


@pytest.mark.parametrize(
    "scenario,expected_error,expected_status,expected_cause",
    [
        ("timeout", LLMTimeoutError, None, APITimeoutError),
        ("connection", LLMConnectionError, None, APIConnectionError),
        ("upstream", LLMUpstreamError, 429, APIStatusError),
        ("invalid", LLMResponseError, 200, TypeError),
    ],
)
def test_call_translates_failures_without_losing_cause_or_metadata(
    offline_call, scenario, expected_error, expected_status, expected_cause,
):
    """真实SDK包装传输异常/HTTP错误，适配层转项目异常且不重试。"""
    prepare, observed = offline_call
    prepare(scenario)

    with pytest.raises(expected_error) as error_info:
        asyncio.run(langchain_adapter.generate_langchain_result("你好"))

    error = error_info.value
    assert len(observed) == 1
    assert error.model == "offline-model"
    assert error.upstream_status == expected_status
    assert error.latency_ms >= 0
    assert isinstance(error.__cause__, expected_cause)


def tool_request(arguments):
    """原始响应的工具参数是字符串；刻意保留空白以检测重新序列化。"""
    return {
        "role": "assistant", "content": None,
        "tool_calls": [{
            "id": "call_001", "type": "function",
            "function": {"name": "calculator", "arguments": arguments},
        }],
    }


def test_tool_request_preserves_raw_arguments_and_round_trip_messages(offline_call):
    """手动串联两次单次调用及真实工具执行，验证声明/回传ID与原始参数。"""
    prepare, observed = offline_call
    raw_arguments = '{ "left": 2, "operator": "+", "right": 3 }'
    request_message = tool_request(raw_arguments)
    prepare("tools", messages=[
        request_message,
        {"role": "assistant", "content": "结果是5。"},
    ])
    history = [{"role": "user", "content": "请用中文回答。"}]
    tools = [deepcopy(CALCULATOR_TOOL)]
    original_tools = deepcopy(tools)

    async def run_scenario():
        first = await langchain_adapter.generate_langchain_result(
            "计算2+3", history, tools=tools,
        )
        assert first.answer is None
        assert first.upstream_status == 200
        assert first.total_tokens == 12
        assert len(first.tool_calls) == 1
        call = first.tool_calls[0]
        assert (call.call_id, call.name, call.arguments) == (
            "call_001", "calculator", raw_arguments,
        )

        tool_result = execute_tool(call)
        assert tool_result == "5"
        additional_messages = [deepcopy(request_message), {
            "role": "tool", "tool_call_id": "call_001", "content": tool_result,
        }]
        original_messages = deepcopy(additional_messages)
        second = await langchain_adapter.generate_langchain_result(
            "计算2+3", history, tools=tools,
            additional_messages=additional_messages,
        )
        assert additional_messages == original_messages
        return second

    result = asyncio.run(run_scenario())

    assert result.answer == "结果是5。"
    assert result.tool_calls == []
    assert len(observed) == 2
    for payload in observed:
        assert payload["tools"] == original_tools
        assert payload["tool_choice"] == "auto"
    sent = observed[1]["messages"]
    assert [message["role"] for message in sent] == [
        "system", "user", "user", "assistant", "tool",
    ]
    assert sent[1] == {"role": "user", "content": "请用中文回答。"}
    assert sent[2] == {"role": "user", "content": "计算2+3"}
    assert sent[3]["tool_calls"][0]["id"] == "call_001"
    assert json.loads(sent[3]["tool_calls"][0]["function"]["arguments"]) == {
        "left": 2, "operator": "+", "right": 3,
    }
    assert sent[4] == {"role": "tool", "tool_call_id": "call_001", "content": "5"}
    assert tools == original_tools
    assert history == [{"role": "user", "content": "请用中文回答。"}]


def test_invalid_tool_json_remains_a_successful_model_result(offline_call):
    """外层协议合法、参数JSON非法：返回真实调用与请求，让工具层拒绝执行。"""
    prepare, observed = offline_call
    prepare("tools", messages=[tool_request("{bad json")])

    result = asyncio.run(langchain_adapter.generate_langchain_result(
        "计算2+3", tools=[CALCULATOR_TOOL],
    ))

    assert len(observed) == 1
    assert isinstance(result, LLMResult)
    assert result.answer is None
    assert result.upstream_status == 200
    assert result.total_tokens == 12
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].arguments == "{bad json"
    with pytest.raises(json.JSONDecodeError):
        execute_tool(result.tool_calls[0])


def test_native_agent_accepts_framework_calls_and_repeats_reference_context(
    offline_call, monkeypatch,
):
    """仅在测试替换模型入口：真实原生循环+框架模型产生项目AgentResult。"""
    prepare, observed = offline_call
    prepare("tools", messages=[
        tool_request('{"left":2,"operator":"+","right":3}'),
        {"role": "assistant", "content": "结果是5。"},
    ])
    monkeypatch.setattr(agent, "generate_reply", langchain_adapter.generate_langchain_result)
    history = [{"role": "assistant", "content": "继续。"}]
    memory_context = 'Memory Context:\n{"language":"zh"}'
    rag_context = "RAG Context:\n仅用于测试的参考文本。"

    result = asyncio.run(agent.run_agent(
        "计算2+3", history, memory_context=memory_context, rag_context=rag_context,
    ))

    assert isinstance(result, agent.AgentResult)
    assert result.answer == "结果是5。"
    assert len(result.model_calls) == len(observed) == 2
    assert result.model_calls[0].answer is None
    assert result.model_calls[0].tool_calls[0].call_id == "call_001"
    assert result.model_calls[1].answer == "结果是5。"
    for call, payload in zip(result.model_calls, observed):
        assert call.upstream_status == 200
        assert call.total_tokens == 12
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1:5] == [
            {"role": "user", "content": memory_context},
            {"role": "user", "content": rag_context},
            {"role": "assistant", "content": "继续。"},
            {"role": "user", "content": "计算2+3"},
        ]
    assert [message["role"] for message in observed[1]["messages"]] == [
        "system", "user", "user", "assistant", "user", "assistant", "tool",
    ]
    assert observed[1]["messages"][-1] == {
        "role": "tool", "tool_call_id": "call_001", "content": "5",
    }
    assert history == [{"role": "assistant", "content": "继续。"}]


@pytest.mark.parametrize("failure", ["timeout", "invalid-arguments"])
def test_native_agent_preserves_framework_call_when_later_work_fails(
    offline_call, monkeypatch, failure,
):
    """模型后续失败与工具参数失败，分别保留真实成功调用及对应原因。"""
    prepare, observed = offline_call
    if failure == "timeout":
        messages = [
            tool_request('{"left":2,"operator":"+","right":3}'),
            httpx.ReadTimeout("offline timeout"),
        ]
        expected_error = agent.AgentRunError
    else:
        messages = [tool_request("{bad json")]
        expected_error = agent.AgentToolError
    prepare("tools", messages=messages)
    monkeypatch.setattr(agent, "generate_reply", langchain_adapter.generate_langchain_result)

    with pytest.raises(expected_error) as caught:
        asyncio.run(agent.run_agent("计算2+3"))

    error = caught.value
    assert len(error.completed_model_calls) == 1
    completed = error.completed_model_calls[0]
    assert completed.upstream_status == 200
    assert completed.total_tokens == 12
    assert completed.tool_calls[0].call_id == "call_001"
    if failure == "timeout":
        assert len(observed) == 2
        assert isinstance(error.cause, LLMTimeoutError)
        assert error.cause.upstream_status is None
        assert isinstance(error.cause.__cause__, APITimeoutError)
    else:
        assert len(observed) == 1
        assert completed.tool_calls[0].arguments == "{bad json"
        assert isinstance(error.cause, json.JSONDecodeError)
