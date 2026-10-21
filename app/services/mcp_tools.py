"""Agent 到 MCP 笔记服务的异步适配层。

校验模型参数，连接 Server，执行 search_notes，再把文本内容块交回 Agent。
Server 错误或缺失文本会抛出异常，由 Agent 的工具失败边界统一承接。
"""

import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent

from app.services.llm import LLMToolCall
from app.tools import SearchNotesArguments


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def execute_mcp_notes(tool_call: LLMToolCall) -> str:
    """通过 MCP 调用笔记工具，并把文本内容块合并成 Agent 工具结果。

    使用当前 Python 解释器与固定项目目录启动 Server，避免 cwd 影响模块查找。
    连接在 async with 内建立并清理；Server 错误或无文本结果会抛出异常。
    """
    arguments = SearchNotesArguments.model_validate(
        json.loads(tool_call.arguments)
    )

    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
        cwd=str(PROJECT_ROOT),
    )

    # 构造 server 只准备配置；进入上下文才启动并连接 Server，退出时清理连接。
    async with Client(server) as client:
        result = await client.call_tool(
            "search_notes",
            {"query": arguments.query},
        )

        # MCP 可以正常返回一个“工具执行失败”的协议结果，必须先检查错误标记。
        if result.is_error:
            raise RuntimeError("MCP 查询工具执行失败")

        # Agent 的 tool 消息需要字符串；只提取 TextContent，不能假定第一个块就是文本。
        texts = []
        for block in result.content:
            if isinstance(block, TextContent):
                texts.append(block.text)

        if not texts:
            raise RuntimeError("MCP 查询工具未返回文本")

        return "\n".join(texts)
