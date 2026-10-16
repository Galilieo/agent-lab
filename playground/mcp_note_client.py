import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent


PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def main() -> None:
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
