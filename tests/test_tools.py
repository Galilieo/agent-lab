import json

import pytest

from pydantic import ValidationError

from app.services.llm import LLMToolCall
from app.tools import execute_tool


def test_execute_tool_searches_markdown_notes_with_source(
    monkeypatch,
    tmp_path,
) -> None:
    notes_dir = tmp_path / "note"
    notes_dir.mkdir()
    (notes_dir / "sample.md").write_text(
        "# 学习笔记\n工具失败会返回502\n计算器用于计算\n",
        encoding="utf-8",
    )
    (notes_dir / "ignored.txt").write_text(
        "工具失败：这不是 Markdown 笔记\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.tools.NOTES_DIR", notes_dir, raising=False)

    tool_call = LLMToolCall(
        call_id="call_notes_001",
        name="search_notes",
        arguments='{"query":"工具失败"}',
    )
    result = execute_tool(tool_call)
    empty_result = execute_tool(
        LLMToolCall(
            call_id="call_notes_001",
            name="search_notes",
            arguments='{"query":"不存在的关键词"}',
        )
    )

    assert json.loads(result) == {
        "query": "工具失败",
        "matches": [
            {
                "path": "notes/sample.md",
                "line": 2,
                "text": "工具失败会返回502",
            }
        ],
    }

    assert json.loads(empty_result) == {
        "query": "不存在的关键词",
        "matches": [],
    }


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
