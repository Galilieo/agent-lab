import json
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator
from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.llm import LLMToolCall


class CalculatorArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: int | float
    operator: Literal["+", "-", "*", "/"]
    right: int | float

    @model_validator(mode="after")
    def reject_division_by_zero(self) -> Self:
        if self.operator == "/" and self.right == 0:
            raise ValueError("division by zero")

        return self


class CurrentTimeArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezone: str


CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "执行两个数字的基础数学计算",
        "parameters": {
            "type": "object",
            "properties": {
                "left": {
                    "type": "number",
                },
                "operator": {
                    "type": "string",
                    "enum": ["+", "-", "*", "/"],
                },
                "right": {
                    "type": "number",
                },
            },
            "required": [
                "left",
                "operator",
                "right",
            ],
            "additionalProperties": False,
        },
    },
}


CURRENT_TIME_TOOL = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "获取指定 IANA 时区的当前日期和时间",
        "parameters": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA 时区名称，例如 Asia/Shanghai 或 UTC",
                },
            },
            "required": ["timezone"],
            "additionalProperties": False,
        },
    },
}

AVAILABLE_TOOLS = [
    CALCULATOR_TOOL,
    CURRENT_TIME_TOOL,
]


def run_calculator(
    arguments: CalculatorArguments,
) -> int | float:
    if arguments.operator == "+":
        return arguments.left + arguments.right

    if arguments.operator == "-":
        return arguments.left - arguments.right

    if arguments.operator == "*":
        return arguments.left * arguments.right

    if arguments.operator == "/":
        return arguments.left / arguments.right


def run_current_time(arguments: CurrentTimeArguments) -> str:
    current_time = datetime.now(ZoneInfo(arguments.timezone))
    return current_time.isoformat()


def execute_tool(tool_call: LLMToolCall) -> str:
    if tool_call.name not in ("calculator", "get_current_time"):
        raise ValueError(f"Unknown tool: {tool_call.name}")

    arguments_data = json.loads(tool_call.arguments)

    if tool_call.name == "calculator":
        arguments = CalculatorArguments.model_validate(arguments_data)
        return str(run_calculator(arguments))

    arguments = CurrentTimeArguments.model_validate(arguments_data)
    return run_current_time(arguments)
