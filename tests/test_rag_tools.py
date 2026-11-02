"""fake 检索验证工具参数边界及资料/来源一致，不调用模型。"""

import asyncio
import json

import pytest
from pydantic import ValidationError

from app.services import rag_tools
from app.services.llm import LLMToolCall
from app.services.rag import DocumentChunk, RetrievedChunk
from app.services.rag_context import RagContext
from app.tools import SEARCH_KNOWLEDGE_TOOL


def search_call(arguments):
    return LLMToolCall("knowledge-1", "search_knowledge", json.dumps(arguments, ensure_ascii=False))


def test_knowledge_tool_preserves_only_delivered_sources_and_application_limits(tmp_path, monkeypatch):
    large = DocumentChunk("notes/large.md", 0, 0, 5000, "长" * 5000)
    small = DocumentChunk("notes/database.md", 1, 10, 14, "及时关闭")
    observed = []

    async def fake_retrieve(question, persist_directory, *, top_k):
        observed.append((question, persist_directory, top_k))
        return [RetrievedChunk(large, 0.0), RetrievedChunk(small, 0.2)]

    monkeypatch.setattr(rag_tools, "retrieve", fake_retrieve)

    result = asyncio.run(rag_tools.execute_knowledge_search(
        search_call({"query": "  为什么释放数据库连接？  "}),
        tmp_path, top_k=2, max_chars=500,
    ))

    assert observed == [("为什么释放数据库连接？", tmp_path, 2)]
    label, body = result.content.split("\n", 1)
    assert label == "RAG Context:"
    assert json.loads(body) == [{
        "id": "notes/database.md::1", "source": "notes/database.md", "chunk_index": 1,
        "start": 10, "end": 14, "text": "及时关闭",
    }]
    assert result.sources == [small]
    assert len(result.content) <= 500
    parameters = SEARCH_KNOWLEDGE_TOOL["function"]["parameters"]
    assert set(parameters["properties"]) == {"query"}
    assert parameters["additionalProperties"] is False


def test_knowledge_tool_rejects_model_paths_and_keeps_empty_results_distinct_from_errors(tmp_path, monkeypatch):
    observed = []
    failure = RuntimeError("synthetic retrieval failure")

    async def fake_retrieve(question, persist_directory, *, top_k):
        observed.append(question)
        if question == "故障":
            raise failure
        return []

    monkeypatch.setattr(rag_tools, "retrieve", fake_retrieve)

    for arguments in ({"query": " \n "}, {"query": "查询", "persist_directory": "/other"}):
        with pytest.raises(ValidationError):
            asyncio.run(rag_tools.execute_knowledge_search(search_call(arguments), tmp_path))
    assert observed == []

    result = asyncio.run(rag_tools.execute_knowledge_search(search_call({"query": "空结果"}), tmp_path))
    assert result == RagContext("", [])

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(rag_tools.execute_knowledge_search(search_call({"query": "故障"}), tmp_path))
    assert caught.value is failure
    assert observed == ["空结果", "故障"]
