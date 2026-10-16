import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent

from app.services.llm import LLMToolCall
from app.tools import SearchNotesArguments


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def execute_mcp_notes(tool_call: LLMToolCall) -> str:
    arguments = SearchNotesArguments.model_validate(
        json.loads(tool_call.arguments)
    )

    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        cwd=str(PROJECT_ROOT),
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "search_notes",
            {"query": arguments.query},
        )

        if result.is_error:
            raise RuntimeError("MCP 查询工具执行失败")

        texts = []
        for block in result.content:
            if isinstance(block, TextContent):
                texts.append(block.text)

        if not texts:
            raise RuntimeError("MCP 查询工具未返回文本")

        return "\n".join(texts)
