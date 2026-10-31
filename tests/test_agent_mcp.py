"""验证 Agent 经 MCP 查询笔记，再把带调用 ID 的结果交回模型。

fake 模型只负责预设工具请求；MCP 协议和临时文件查询真实执行。
fixture 将 stdio 启动配置替换为同进程连接，避免测试依赖外部子进程。
"""

import asyncio
import json

import pytest
from mcp import Client, StdioServerParameters

from app.mcp_server import mcp
from app.services.agent import run_agent
from app.services.llm import LLMResult, LLMToolCall


@pytest.fixture
def notes_mcp_scenario(monkeypatch, tmp_path):
    """准备临时笔记和同进程 MCP，记录协议调用与 fake 模型收到的工具消息。"""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "sample.md").write_text(
        "# 学习笔记\n工具失败会返回502\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("app.tools.NOTES_DIR", notes_dir)

    observed = {"servers": [], "mcp_calls": [], "model_messages": []}
    original_init = Client.__init__
    original_call_tool = Client.call_tool

    def use_in_process_server(self, server, *args, **kwargs):
        if not isinstance(server, StdioServerParameters):
            raise AssertionError("Expected stdio server configuration")
        observed["servers"].append(server)
        # 保留真实 MCP 协议调用，测试中改用同进程 Server 和临时笔记。
        original_init(self, mcp, *args, **kwargs)

    async def record_mcp_call(self, name, arguments=None, **kwargs):
        observed["mcp_calls"].append((name, arguments))
        return await original_call_tool(self, name, arguments, **kwargs)

    monkeypatch.setattr(Client, "__init__", use_in_process_server)
    monkeypatch.setattr(Client, "call_tool", record_mcp_call)

    async def fake_generate_reply(
        message,
        history=None,
        tools=None,
        additional_messages=None,
        *,
        system_prompt=None,
        memory_context="",
        rag_context="",
    ):
        # 保存快照，避免 Agent 后续修改同一个列表影响观察结果。
        observed["model_messages"].append(
            list(additional_messages or [])
        )
        call_number = len(observed["model_messages"])
        if call_number > 2:
            raise AssertionError("Expected only two model calls")

        return LLMResult(
            answer=None if call_number == 1 else "查询完成。",
            model="fake-model",
            upstream_status=200,
            latency_ms=1.0,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            tool_calls=(
                [
                    LLMToolCall(
                        call_id="call_notes_mcp_001",
                        name="search_notes",
                        arguments='{"query":"工具失败"}',
                    )
                ]
                if call_number == 1
                else []
            ),
        )

    monkeypatch.setattr(
        "app.services.agent.generate_reply",
        fake_generate_reply,
    )
    return observed


def test_run_agent_returns_notes_mcp_result_to_model(notes_mcp_scenario):
    """验证查询实际经过 MCP，tool_call_id 正确关联，并把真实查询结果回传模型。"""
    observed = notes_mcp_scenario
    result = asyncio.run(run_agent(message="查一下工具失败的笔记"))
    assistant_message, tool_message = observed["model_messages"][1][-2:]
    notes_result = json.loads(tool_message["content"])

    assert observed["mcp_calls"] == [("search_notes", {"query": "工具失败"})]

    assert assistant_message["role"] == "assistant"
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call_notes_mcp_001"
    assert (
        tool_message["tool_call_id"]
        == assistant_message["tool_calls"][0]["id"]
    )

    assert notes_result == {
        "query": "工具失败",
        "matches": [
            {
                "path": "notes/sample.md",
                "line": 2,
                "text": "工具失败会返回502",
            }
        ],
    }

    assert result.answer == "查询完成。"
    assert len(result.model_calls) == 2
