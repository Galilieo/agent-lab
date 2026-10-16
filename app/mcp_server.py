import json
from pathlib import Path

from mcp.server import MCPServer

from app.tools import SearchNotesArguments, run_search_notes

mcp = MCPServer("agent-lab-notes")


@mcp.tool()
def search_notes(query: str) -> str:
    """按关键词查询项目 notes 目录中的 Markdown 笔记。"""
    arguments = SearchNotesArguments.model_validate({"query": query})
    result = run_search_notes(arguments)
    return json.dumps(result, ensure_ascii=False)


@mcp.resource(
    "notes://learning-route",
    mime_type="text/markdown",
)
def learning_route() -> str:
    """提供项目学习路线的完整内容。"""
    route_file = (
        Path(__file__).resolve().parent.parent
        / "notes"
        / "agent-lab总体学习路线.md"
    )
    return route_file.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="stdio")
