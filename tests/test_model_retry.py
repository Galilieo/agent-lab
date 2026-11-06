"""真实重试策略/Agent/计算器配合假模型函数，不调用HTTP或业务数据库。"""

import asyncio
from copy import deepcopy
from functools import partial
import logging

import pytest

from app.services import agent, model_retry
from app.services.llm import LLMResult, LLMTimeoutError, LLMToolCall, LLMUpstreamError


def test_retry_after_tool_reuses_messages_without_executing_calculator_again(monkeypatch, caplog):
    """后续模型超时后仅重试该次操作，工具一次、实际模型尝试三次。"""
    observed = []
    executions = []
    waits = []
    real_execute = agent.execute_tool

    async def fake_generate(**kwargs):
        observed.append(deepcopy(kwargs))
        if len(observed) == 2:
            raise LLMTimeoutError(
                "synthetic private transport detail", model="offline-model",
                upstream_status=None, latency_ms=12.0,
            )
        return LLMResult(
            answer=None if len(observed) == 1 else "结果是5。",
            model="offline-model", upstream_status=200, latency_ms=1.0,
            prompt_tokens=None, completion_tokens=None, total_tokens=None,
            tool_calls=[LLMToolCall("calc-1", "calculator", '{"left":2,"operator":"+","right":3}')]
            if len(observed) == 1 else [],
        )

    async def fake_sleep(seconds):
        waits.append(seconds)

    async def wrapped_generate(**kwargs):
        return await model_retry.retry_model_call(
            partial(fake_generate, **kwargs), max_attempts=2, delay_seconds=0.25,
        )

    def observed_execute(call):
        executions.append(call)
        return real_execute(call)

    monkeypatch.setattr(agent, "generate_reply", wrapped_generate)
    monkeypatch.setattr(agent, "execute_tool", observed_execute)
    monkeypatch.setattr(model_retry, "sleep", fake_sleep)
    with caplog.at_level(logging.WARNING, logger="app.services.model_retry"):
        result = asyncio.run(agent.run_agent("计算2+3"))

    assert result.answer == "结果是5。"
    assert len(result.model_calls) == 2
    assert len(observed) == 3
    assert len(executions) == 1
    assert observed[1] == observed[2]
    assert observed[2]["additional_messages"][-1] == {
        "role": "tool", "tool_call_id": "calc-1", "content": "5",
    }
    assert waits == [0.25]
    assert any("attempt=1" in record.message and "retry=True" in record.message for record in caplog.records)
    assert "synthetic private transport detail" not in caplog.text
    assert "计算2+3" not in caplog.text


@pytest.mark.parametrize("case", ["unauthorized", "exhausted", "cancelled"])
def test_retry_stops_at_policy_boundary_and_keeps_original_error(monkeypatch, case):
    """401不重试、持续超时最多两次，取消不吞掉；不等待最后一次之后。"""
    attempts = []
    waits = []
    if case == "cancelled":
        error = asyncio.CancelledError()
    elif case == "unauthorized":
        error = LLMUpstreamError("synthetic failure", model="offline-model", upstream_status=401, latency_ms=1)
    else:
        error = LLMTimeoutError("synthetic failure", model="offline-model", upstream_status=None, latency_ms=1)

    async def fail():
        attempts.append(1)
        raise error

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setattr(model_retry, "sleep", fake_sleep)
    with pytest.raises(type(error)) as caught:
        asyncio.run(model_retry.retry_model_call(fail, max_attempts=2, delay_seconds=0.25))
    assert caught.value is error
    assert len(attempts) == (2 if case == "exhausted" else 1)
    assert waits == ([0.25] if case == "exhausted" else [])
