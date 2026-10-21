"""把本地笔记查询与学习路线读取暴露为独立 MCP Server。

通过 python -m app.mcp_server 运行，使用 stdio 与 Client 通信。
Server 执行真实笔记读取，不调用模型，也不自行把 Resource 注入 Agent 上下文。
"""

import json
from pathlib import Path

from mcp.server import MCPServer

from app.tools import SearchNotesArguments, run_search_notes

mcp = MCPServer("agent-lab-notes")


# 注册可执行操作；参数校验和笔记读取复用本地实现，避免 Server 复制业务规则。
@mcp.tool()
def search_notes(query: str) -> str:
    """按关键词查询项目 notes 目录中的 Markdown 笔记。"""
    arguments = SearchNotesArguments.model_validate({"query": query})
    result = run_search_notes(arguments)
    return json.dumps(result, ensure_ascii=False)


# Resource URI 是协议资源标识，实际文件位置由函数内固定路径决定。
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
    # stdio 用于协议通信；不要向 stdout 打印普通调试内容干扰 Client。
    mcp.run(transport="stdio")
