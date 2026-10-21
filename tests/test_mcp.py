"""用同进程 MCP Client/Server 验证工具发现和调用结果格式。

查询真实临时笔记，不启动 stdio 子进程，也不请求模型。
独立 stdio 启动实验由 playground/mcp_note_client.py 提供。
"""

import asyncio
import json

from mcp import Client
from mcp.types import TextContent

from app.mcp_server import mcp


def test_mcp_lists_and_calls_notes_tool(monkeypatch, tmp_path) -> None:
    """验证 MCP 工具名称、必填参数、成功标记以及带出处的 JSON 文本内容。"""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "sample.md").write_text(
        "# 学习笔记\n工具失败会返回502\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.tools.NOTES_DIR", notes_dir)

    async def query_notes():
        # 直接传入 Server 对象使用同进程连接，仍真实经过 MCP 的发现与调用接口。
        async with Client(mcp) as client:
            listed = await client.list_tools()
            result = await client.call_tool(
                "search_notes",
                {"query": "工具失败"},
            )
            return listed, result

    listed, result = asyncio.run(query_notes())

    assert [tool.name for tool in listed.tools] == ["search_notes"]
    assert listed.tools[0].input_schema["required"] == ["query"]

    assert result.is_error is False
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)

    assert json.loads(result.content[0].text) == {
        "query": "工具失败",
        "matches": [
            {
                "path": "notes/sample.md",
                "line": 2,
                "text": "工具失败会返回502",
            }
        ],
    }
