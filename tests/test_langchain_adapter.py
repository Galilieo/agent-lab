"""运行真实模板/ChatDeepSeek/SDK，以假HTTP验证普通调用的项目契约。

HTTP钩子保持真实执行，不直接伪造AIMessage或SDK异常；不访问模型服务。
"""

import asyncio
import json

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError

from app.services import langchain_adapter
from app.services.llm import (
    LLMConnectionError,
    LLMResponseError,
    LLMResult,
    LLMTimeoutError,
    LLMUpstreamError,
)


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

    def prepare(scenario):
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
