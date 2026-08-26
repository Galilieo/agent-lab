import asyncio

import httpx

import pytest

from app.services.agent import AgentRunError, run_agent
from app.services.llm import (
    LLMResult,
    LLMTimeoutError,
    LLMToolCall,
)


def test_run_agent_returns_final_answer_after_calculator_tool_call(
    monkeypatch,
) -> None:
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
    call_count = 0
    observed_tool_names = []
    observed_tool_results = []

    async def fake_generate_reply(
        message: str,
        history=None,
        tools=None,
        additional_messages=None,
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
        ["calculator"],
        ["calculator"],
        ["calculator"],
    ]
    assert observed_tool_results == [
        [],
        ["5"],
        ["5", "20"],
    ]


def test_run_agent_stops_before_executing_tool_when_call_budget_is_exhausted(
    monkeypatch,
) -> None:
    model_call_count = 0
    executed_tool_call_ids = []

    async def fake_generate_reply(
        message: str,
        history=None,
        tools=None,
        additional_messages=None,
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

    with pytest.raises(
        RuntimeError,
        match="Agent reached the maximum number of model calls",
    ):
        asyncio.run(
            run_agent(
                message="一直调用 calculator",
                max_model_calls=2,
            )
        )

    assert model_call_count == 2
    assert executed_tool_call_ids == ["call_001"]


def test_run_agent_preserves_completed_call_when_final_call_times_out(
    monkeypatch,
) -> None:
    call_count = 0

    async def fake_generate_reply(
        message: str,
        history=None,
        tools=None,
        additional_messages=None,
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
