"""验证原生 Agent 的工具循环、消息回传、调用预算与失败记录。

模型响应由 fake HTTP Client 或 fake generate_reply 预设。
成功链执行真实本地工具；预算测试替换工具入口以观察执行次数。
这些测试保护程序链路，不能证明真实模型会选择正确工具。
"""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

import pytest

from app.services.agent import (
    AgentModelCallLimitError,
    AgentRunError,
    run_agent,
)
from app.services.llm import (
    LLMResult,
    LLMTimeoutError,
    LLMToolCall,
)


def test_run_agent_returns_final_answer_after_current_time_tool_call(
    monkeypatch,
) -> None:
    """预设模型选择时间工具，验证真实时间执行、UTC offset、调用 ID 和最终回答。"""
    observed_payloads = []
    tool_arguments = '{"timezone":"Asia/Shanghai"}'

    class CurrentTimeAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed_payloads.append(json)

            if len(observed_payloads) == 1:
                response_message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_time_001",
                            "type": "function",
                            "function": {
                                "name": "get_current_time",
                                "arguments": tool_arguments,
                            },
                        }
                    ],
                }
            elif len(observed_payloads) == 2:
                response_message = {
                    "role": "assistant",
                    "content": "上海当前时间已获取。",
                }
            else:
                raise AssertionError("Expected only two model requests")

            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": response_message}]},
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        CurrentTimeAsyncClient,
    )

    before = datetime.now(timezone.utc)
    result = asyncio.run(run_agent(message="上海现在几点？"))
    after = datetime.now(timezone.utc)

    assert result.answer == "上海当前时间已获取。"
    assert len(result.model_calls) == 2
    assert len(observed_payloads) == 2

    for payload in observed_payloads:
        assert [
            tool["function"]["name"]
            for tool in payload["tools"]
        ] == ["calculator", "get_current_time", "search_notes"]

    assistant_message, tool_message = (
        observed_payloads[1]["messages"][-2:]
    )

    assert assistant_message["role"] == "assistant"
    assert assistant_message["content"] is None

    requested_call = assistant_message["tool_calls"][0]
    assert requested_call["function"] == {
        "name": "get_current_time",
        "arguments": tool_arguments,
    }

    assert tool_message["role"] == "tool"
    assert (
        requested_call["id"]
        == tool_message["tool_call_id"]
        == "call_time_001"
    )

    reported_time = datetime.fromisoformat(tool_message["content"])
    assert reported_time.utcoffset() == timedelta(hours=8)
    assert before <=reported_time <= after


def test_run_agent_returns_final_answer_after_calculator_tool_call(
    monkeypatch,
) -> None:
    """验证 calculator 工具请求、执行结果和第二次模型请求组成完整闭环。"""
    observed_payloads = []

    class AgentLoopAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed_payloads.append(json)

            if len(observed_payloads) == 1:
                return httpx.Response(
                    200,
                    request=httpx.Request("POST", url),
                    json={
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call_001",
                                            "type": "function",
                                            "function": {
                                                "name": "calculator",
                                                "arguments": (
                                                    '{"left":2,'
                                                    '"operator":"+",'
                                                    '"right":3}'
                                                ),
                                            },
                                        }
                                    ],
                                }
                            }
                        ],
                    },
                )
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "2 + 3 = 5",
                            }
                        }
                    ],
                },
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        AgentLoopAsyncClient,
    )

    result = asyncio.run(
        run_agent(message="计算2 + 3")
    )

    assert result.answer == "2 + 3 = 5"
    assert len(result.model_calls) == 2
    assert result.model_calls[0].answer is None
    assert result.model_calls[0].tool_calls[0].call_id == "call_001"
    assert result.model_calls[1].answer == "2 + 3 = 5"
    assert len(observed_payloads) == 2
    assert (
        observed_payloads[0]["tools"][0]["function"]["name"] == "calculator"
    )
    assert observed_payloads[1]["messages"][-2:] == [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "arguments": (
                            '{"left":2,'
                            '"operator":"+",'
                            '"right":3}'
                        ),
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_001",
            "content": "5",
        },
    ]


def test_run_agent_repeats_tool_calls_until_model_returns_final_answer(
    monkeypatch,
) -> None:
    """验证连续两次工具执行与第三次最终回答，每轮都提供可用工具并保留旧结果。"""
    call_count = 0
    observed_tool_names = []
    observed_tool_results = []

    async def fake_generate_reply(
        message: str,
        history=None,
        tools=None,
        additional_messages=None,
        *,
        system_prompt=None,
    ) -> LLMResult:
        nonlocal call_count
        call_count += 1

        observed_tool_names.append(
            [
                tool["function"]["name"]
                for tool in tools or []
            ]
        )
        observed_tool_results.append(
            [
                item["content"]
                for item in additional_messages or []
                if item["role"] == "tool"
            ]
        )

        if call_count == 1:
            return LLMResult(
                answer=None,
                model="fake-model",
                upstream_status=200,
                latency_ms=5.0,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                tool_calls=[
                    LLMToolCall(
                        call_id="call_001",
                        name="calculator",
                        arguments=(
                            '{"left":2,"operator":"+","right":3}'
                        ),
                    )
                ],
            )

        if call_count == 2:
            return LLMResult(
                answer=None,
                model="fake-model",
                upstream_status=200,
                latency_ms=5.0,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                tool_calls=[
                    LLMToolCall(
                        call_id="call_002",
                        name="calculator",
                        arguments=(
                            '{"left":5,"operator":"*","right":4}'
                        ),
                    )
                ],
            )

        return LLMResult(
            answer="最终结果是 20",
            model="fake-model",
            upstream_status=200,
            latency_ms=5.0,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
        )

    monkeypatch.setattr(
        "app.services.agent.generate_reply",
        fake_generate_reply,
    )

    result = asyncio.run(
        run_agent(
            message="先计算 2 + 3, 再乘以 4",
            max_model_calls=3,
        )
    )

    assert result.answer == "最终结果是 20"
    assert len(result.model_calls) == 3
    assert call_count == 3
    assert observed_tool_names == [
        ["calculator", "get_current_time", "search_notes"],
        ["calculator", "get_current_time", "search_notes"],
        ["calculator", "get_current_time", "search_notes"],
    ]
    assert observed_tool_results == [
        [],
        ["5"],
        ["5", "20"],
    ]


def test_run_agent_stops_before_executing_tool_when_call_budget_is_exhausted(
    monkeypatch,
) -> None:
    """验证预算在执行下一工具前生效，避免没有后续模型预算时再产生工具动作。"""
    model_call_count = 0
    executed_tool_call_ids = []

    async def fake_generate_reply(
        message: str,
        history=None,
        tools=None,
        additional_messages=None,
        *,
        system_prompt=None,
    ) -> LLMResult:
        nonlocal model_call_count
        model_call_count += 1

        return LLMResult(
            answer=None,
            model="fake-model",
            upstream_status=200,
            latency_ms=5.0,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            tool_calls=[
                LLMToolCall(
                    call_id=f"call_{model_call_count:03d}",
                    name="calculator",
                    arguments=(
                        '{"left":2,"operator":"+","right":3}'
                    ),
                )
            ],
        )

    def fake_execute_tool(tool_call: LLMToolCall) -> str:
        executed_tool_call_ids.append(tool_call.call_id)
        return "5"

    monkeypatch.setattr(
        "app.services.agent.generate_reply",
        fake_generate_reply,
    )
    monkeypatch.setattr(
        "app.services.agent.execute_tool",
        fake_execute_tool,
    )

    with pytest.raises(AgentModelCallLimitError) as error_info:
        asyncio.run(
            run_agent(
                message="一直调用 calculator",
                max_model_calls=2,
            )
        )

    error = error_info.value
    assert model_call_count == 2
    assert executed_tool_call_ids == ["call_001"]
    assert [
        model_call.tool_calls[0].call_id
        for model_call in error.completed_model_calls
    ] == ["call_001", "call_002"]


def test_run_agent_preserves_completed_call_when_final_call_times_out(
    monkeypatch,
) -> None:
    """验证后续请求超时时，AgentRunError 携带真实原因及此前成功调用。"""
    call_count = 0

    async def fake_generate_reply(
        message: str,
        history=None,
        tools=None,
        additional_messages=None,
        *,
        system_prompt=None,
    ) -> LLMResult:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return LLMResult(
                answer=None,
                model="fake-model",
                upstream_status=200,
                latency_ms=5.0,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                tool_calls=[
                    LLMToolCall(
                        call_id="call_001",
                        name="calculator",
                        arguments=(
                            '{"left":2,"operator":"+","right":3}'
                        ),
                    )
                ],
            )

        raise LLMTimeoutError(
            "LLM request timed out.",
            model="fake-model",
            upstream_status=None,
            latency_ms=60000.0,
        )

    monkeypatch.setattr(
        "app.services.agent.generate_reply",
        fake_generate_reply,
    )

    with pytest.raises(AgentRunError) as error_info:
        asyncio.run(run_agent(message="计算 2 + 3"))

    error = error_info.value

    assert isinstance(error.cause, LLMTimeoutError)
    assert len(error.completed_model_calls) == 1
    assert (
        error.completed_model_calls[0].tool_calls[0].call_id == "call_001"
    )
