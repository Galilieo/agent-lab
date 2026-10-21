"""通过 stdio 启动真实 MCP Server 的独立 Client 实验。

在仓库根目录运行 uv run python playground/mcp_note_client.py。
它会启动子进程、列出工具并查询真实 notes 文件，不调用 LLM。
"""

import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent


PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def main() -> None:
    """启动并连接 stdio Server，列出工具，再查询并打印文本结果。

    StdioServerParameters 只描述启动方式，进入 Client 上下文才实际连接。
    """
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        cwd=str(PROJECT_ROOT),
    )

    async with Client(server) as client:
        listed = await client.list_tools()
        print("可用工具：", [tool.name for tool in listed.tools])

        result = await client.call_tool(
            "search_notes",
            {"query": "工具失败"},
        )

        if result.is_error:
            raise RuntimeError("MCP 查询工具执行失败")

        for block in result.content:
            if isinstance(block, TextContent):
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
