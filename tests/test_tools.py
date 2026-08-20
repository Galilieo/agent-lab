import pytest

from pydantic import ValidationError

from app.services.llm import LLMToolCall
from app.tools import execute_tool


def test_execute_tool_validates_and_runs_calculator() -> None:
    tool_call = LLMToolCall(
        call_id="call_001",
        name="calculator",
        arguments='{"left":2,"operator":"+","right":3}',
    )

    result = execute_tool(tool_call)

    assert result == "5"


def test_execute_tool_rejects_calculator_division_by_zero() -> None:
    tool_call = LLMToolCall(
        call_id="call_002",
        name="calculator",
        arguments='{"left":2,"operator":"/","right":0}',
    )

    with pytest.raises(
        ValidationError,
        match="division by zero",
    ):
        execute_tool(tool_call)
