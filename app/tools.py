import json
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

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


def execute_tool(tool_call: LLMToolCall) -> str:
    if tool_call.name != "calculator":
        raise ValueError(f"Unknown tool: {tool_call.name}")

    arguments_data = json.loads(tool_call.arguments)
    arguments = CalculatorArguments.model_validate(arguments_data)
    result = run_calculator(arguments)

    return str(result)
