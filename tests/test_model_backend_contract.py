"""同组离线响应分别驱动原生模型入口与LangChain适配入口。

两者共用真实原生Agent循环和计算器，验证项目结果/失败契约。
仅模型HTTP为预设；不是两个Agent编排器或真实模型效果的对比。
"""

import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import httpx
import pytest

from app.services import agent, langchain_adapter, llm


@pytest.fixture(params=["native", "langchain"])
def backend_run(request, monkeypatch):
    """共用传输替身，仅选择Agent调用的单次模型实现。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(llm.settings, "openai_api_key", "offline-placeholder")
    monkeypatch.setattr(llm.settings, "openai_base_url", "https://example.invalid/v1")
    monkeypatch.setattr(llm.settings, "openai_model", "offline-model")
    observed = []

    async def run(messages, *, history, memory_context, rag_context):
        pending = iter(messages)

        def respond(http_request):
            observed.append(json.loads(http_request.content))
            message = next(pending)
            if message == "timeout":
                raise httpx.ReadTimeout("offline timeout", request=http_request)
            return httpx.Response(200, json={
                "id": "offline-contract", "object": "chat.completion", "created": 0,
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

        if request.param == "native":
            # 只换llm模块所引用的httpx对象，避免修改SDK使用的全局AsyncClient类。
            monkeypatch.setattr(llm, "httpx", SimpleNamespace(
                AsyncClient=create_client,
                ReadTimeout=httpx.ReadTimeout,
                ConnectError=httpx.ConnectError,
                HTTPStatusError=httpx.HTTPStatusError,
            ))
            model_call = llm.generate_reply
        else:
            monkeypatch.setattr(langchain_adapter, "AsyncClient", create_client)
            model_call = langchain_adapter.generate_langchain_result

        monkeypatch.setattr(agent, "generate_reply", model_call)
        return await agent.run_agent(
            "计算2+3", history,
            memory_context=memory_context,
            rag_context=rag_context,
        )

    return run, observed


@pytest.mark.parametrize("scenario", ["success", "second-timeout", "invalid-arguments"])
def test_model_backends_follow_the_same_agent_contract(backend_run, scenario):
    """同一断言契约覆盖两种模型实现，比较字段与错误归属，不比较耗时数值。"""
    run, observed = backend_run
    raw_arguments = (
        "{bad json" if scenario == "invalid-arguments"
        else '{ "left": 2, "operator": "+", "right": 3 }'
    )
    request_message = {
        "role": "assistant", "content": None,
        "tool_calls": [{
            "id": "call_shared", "type": "function",
            "function": {"name": "calculator", "arguments": raw_arguments},
        }],
    }
    messages = [request_message]
    if scenario == "success":
        messages.append({"role": "assistant", "content": "结果是5。"})
    elif scenario == "second-timeout":
        messages.append("timeout")
    history = [{"role": "assistant", "content": "继续。"}]
    original_history = deepcopy(history)
    original_messages = deepcopy(messages)
    memory_context = 'Memory Context:\n{"language":"zh"}'
    rag_context = "RAG Context:\n测试参考文本。"

    def invoke():
        return asyncio.run(run(
            messages, history=history,
            memory_context=memory_context, rag_context=rag_context,
        ))

    if scenario == "success":
        result = invoke()
        assert isinstance(result, agent.AgentResult)
        assert result.answer == "结果是5。"
        calls = result.model_calls
        assert len(calls) == len(observed) == 2
        assert calls[1].answer == "结果是5。"
        assert calls[1].tool_calls == []
    else:
        expected_error = (
            agent.AgentRunError if scenario == "second-timeout"
            else agent.AgentToolError
        )
        with pytest.raises(expected_error) as caught:
            invoke()
        calls = caught.value.completed_model_calls
        assert len(calls) == 1
        if scenario == "second-timeout":
            assert len(observed) == 2
            assert isinstance(caught.value.cause, llm.LLMTimeoutError)
            assert caught.value.cause.outcome == "timeout"
            assert caught.value.cause.upstream_status is None
        else:
            assert len(observed) == 1
            assert isinstance(caught.value.cause, json.JSONDecodeError)

    assert calls[0].answer is None
    assert len(calls[0].tool_calls) == 1
    call = calls[0].tool_calls[0]
    assert (call.call_id, call.name, call.arguments) == (
        "call_shared", "calculator", raw_arguments,
    )
    for model_call in calls:
        assert model_call.model == "offline-model"
        assert model_call.upstream_status == 200
        assert model_call.latency_ms >= 0
        assert (model_call.prompt_tokens, model_call.completion_tokens, model_call.total_tokens) == (8, 4, 12)
    for payload in observed:
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][1:5] == [
            {"role": "user", "content": memory_context},
            {"role": "user", "content": rag_context},
            {"role": "assistant", "content": "继续。"},
            {"role": "user", "content": "计算2+3"},
        ]
        assert [tool["function"]["name"] for tool in payload["tools"]] == [
            "calculator", "get_current_time", "search_notes",
        ]
        assert payload["tool_choice"] == "auto"
    if len(observed) == 2:
        assistant_message, tool_message = observed[1]["messages"][-2:]
        assert assistant_message["role"] == "assistant"
        assert assistant_message["tool_calls"][0]["id"] == "call_shared"
        assert json.loads(assistant_message["tool_calls"][0]["function"]["arguments"]) == {
            "left": 2, "operator": "+", "right": 3,
        }
        assert tool_message == {"role": "tool", "tool_call_id": "call_shared", "content": "5"}
    assert history == original_history
    assert messages == original_messages
