"""声明模型可见的工具，并校验、执行本地工具参数。

工具声明描述模型可以请求什么；Pydantic 模型限制参数形状；执行函数产生结果。
Agent 中的笔记查询走 MCP，计算器和时间查询直接走本地执行入口。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.llm import LLMToolCall


NOTES_DIR = Path(__file__).resolve().parent.parent / "notes"


# 计算器的本地参数契约；只允许四种运算，并拒绝未声明字段。
class CalculatorArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left: int | float
    operator: Literal["+", "-", "*", "/"]
    right: int | float

    # after 阶段可以读取已通过字段校验的值，再检查运算符与右操作数组合是否合法。
    @model_validator(mode="after")
    def reject_division_by_zero(self) -> Self:
        if self.operator == "/" and self.right == 0:
            raise ValueError("division by zero")

        return self


# 笔记查询参数；先去掉首尾空白，再拒绝空关键词和额外字段。
class SearchNotesArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(min_length=1)


# 时间工具参数；只验证字段形状，时区名称由 ZoneInfo 执行时验证。
class CurrentTimeArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezone: str


# 这些声明进入模型请求，描述可用工具；真正执行前仍要通过上面的参数模型校验。
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


# 每轮提供的可用能力清单，不是已经执行的工具或执行结果。
AVAILABLE_TOOLS = [
    CALCULATOR_TOOL,
    CURRENT_TIME_TOOL,
    SEARCH_NOTES_TOOL,
]


def run_calculator(
    arguments: CalculatorArguments,
) -> int | float:
    """执行已经通过参数校验的四则运算；除零由参数模型提前拒绝。"""
    if arguments.operator == "+":
        return arguments.left + arguments.right

    if arguments.operator == "-":
        return arguments.left - arguments.right

    if arguments.operator == "*":
        return arguments.left * arguments.right

    if arguments.operator == "/":
        return arguments.left / arguments.right


def run_current_time(arguments: CurrentTimeArguments) -> str:
    """返回目标时区的 ISO 8601 当前时间，结果包含 UTC offset。"""
    current_time = datetime.now(ZoneInfo(arguments.timezone))
    return current_time.isoformat()


def run_search_notes(arguments: SearchNotesArguments) -> dict:
    """在固定 notes 目录按字面关键词查询 Markdown，最多返回五条。

    每条结果包含文件路径、从 1 开始的行号和原文；不命中时正常返回空列表。
    仅扫描目录下的普通 .md 文件，不递归，也不跟随符号链接。
    """
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
    """按工具名解析、校验并执行本地工具，统一返回可放入 tool 消息的字符串。

    未知工具、非法 JSON、参数错误与执行错误继续向外抛出，交给 Agent 包装。
    Agent 的 search_notes 分支目前使用 MCP，本地笔记分支仍供直接调用与测试使用。
    """
    if tool_call.name not in (
        "calculator",
        "get_current_time",
        "search_notes",
    ):
        raise ValueError(f"Unknown tool: {tool_call.name}")

    # 参数最初是模型返回的 JSON 字符串，先解码，再按具体工具进行 Schema 校验。
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
