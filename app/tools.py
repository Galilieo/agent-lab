import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.llm import LLMToolCall


NOTES_DIR = Path(__file__).resolve().parent.parent / "notes"


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


class SearchNotesArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(min_length=1)


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


SEARCH_NOTES_TOOL = {
    "type": "function",
    "function": {
        "name": "search_notes",
        "description": "按关键词查询项目 notes 目录中的 Markdown 笔记",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "需要查找的非空关键词",
                    "minLength": 1,
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


AVAILABLE_TOOLS = [
    CALCULATOR_TOOL,
    CURRENT_TIME_TOOL,
    SEARCH_NOTES_TOOL,
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


def run_search_notes(arguments: SearchNotesArguments) -> dict:
    if not NOTES_DIR.is_dir():
        raise FileNotFoundError("Notes directory does not exist")

    matches = []

    for note_file in sorted(NOTES_DIR.glob("*.md")):
        if not note_file.is_file() or note_file.is_symlink():
            continue

        content = note_file.read_text(encoding="utf-8")

        for line_number, text in enumerate(content.splitlines(), start=1):
            if arguments.query in text:
                matches.append(
                    {
                        "path": f"notes/{note_file.name}",
                        "line": line_number,
                        "text": text,
                    }
                )

                if len(matches) >= 5:
                    return {"query": arguments.query, "matches": matches}

    return {"query": arguments.query, "matches": matches}


def execute_tool(tool_call: LLMToolCall) -> str:
    if tool_call.name not in (
        "calculator",
        "get_current_time",
        "search_notes",
    ):
        raise ValueError(f"Unknown tool: {tool_call.name}")

    arguments_data = json.loads(tool_call.arguments)

    if tool_call.name == "calculator":
        arguments = CalculatorArguments.model_validate(arguments_data)
        return str(run_calculator(arguments))

    if tool_call.name == "get_current_time":
        arguments = CurrentTimeArguments.model_validate(arguments_data)
        return run_current_time(arguments)

    arguments = SearchNotesArguments.model_validate(arguments_data)
    result = run_search_notes(arguments)
    return json.dumps(result, ensure_ascii=False)
