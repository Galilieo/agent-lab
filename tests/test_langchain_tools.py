"""验证框架计算器适配、原生校验复用与工具结果关联。

真实执行 StructuredTool、CalculatorArguments 和计算器，不调用模型或 HTTP。
输入工具请求为预设数据，不据此宣称真实模型会选择计算器或生成正确参数。
"""

import asyncio

import pytest
from langchain_core.messages import ToolMessage
from pydantic import ValidationError

from app.services import langchain_tools


@pytest.fixture(autouse=True)
def disable_tool_tracing(monkeypatch):
    """阻止工具测试因外部运行环境的追踪配置联网。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")


def test_calculator_tool_executes_and_preserves_tool_call_id() -> None:
    """完整工具请求经真实计算后，返回携带同一调用 ID 的结果消息。"""
    tool = langchain_tools.build_calculator_tool()

    result = asyncio.run(tool.ainvoke({
        "type": "tool_call",
        "id": "call_001",
        "name": "calculator",
        "args": {"left": 2, "operator": "+", "right": 3},
    }))

    assert isinstance(result, ToolMessage)
    assert result.content == "5"
    assert result.tool_call_id == "call_001"
    assert result.name == "calculator"


def test_calculator_tool_rejects_division_by_zero_with_existing_schema() -> None:
    """非法组合由参数模型拒绝，不能执行除零或伪装成正常工具结果。"""
    tool = langchain_tools.build_calculator_tool()

    with pytest.raises(ValidationError, match="division by zero"):
        asyncio.run(tool.ainvoke({
            "type": "tool_call",
            "id": "call_invalid",
            "name": "calculator",
            "args": {"left": 2, "operator": "/", "right": 0},
        }))
