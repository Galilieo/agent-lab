"""验证参考原文、稳定引用 ID、来源对应与完整字符预算；不调用模型。"""

import json

import pytest

from app.services import rag_context
from app.services.rag import DocumentChunk, RetrievedChunk


def test_rag_context_preserves_reference_records_and_matching_sources():
    first = DocumentChunk("notes/database.md", 0, 0, 5, "关闭数据库")
    second = DocumentChunk("notes/memory.md", 1, 10, 14, "会话记忆")
    hits = [RetrievedChunk(first, 0.1), RetrievedChunk(second, 0.4)]
    before = list(hits)

    context = rag_context.build_rag_context(hits)

    label, body = context.content.split("\n", 1)
    assert label == "RAG Context:"
    assert json.loads(body) == [
        {"id": "notes/database.md::0", "source": "notes/database.md", "chunk_index": 0,
         "start": 0, "end": 5, "text": "关闭数据库"},
        {"id": "notes/memory.md::1", "source": "notes/memory.md", "chunk_index": 1,
         "start": 10, "end": 14, "text": "会话记忆"},
    ]
    assert context.sources == [first, second]
    assert hits == before


def test_rag_context_budget_skips_whole_chunks_and_keeps_sources_aligned():
    large = DocumentChunk("notes/long.md", 0, 0, 500, "长" * 500)
    text = '事务。\n"引用"'
    small = DocumentChunk("notes/short.md", 0, 0, len(text), text)
    hits = [RetrievedChunk(large, 0.1), RetrievedChunk(small, 0.4)]
    record = {
        "id": "notes/short.md::0", "source": "notes/short.md", "chunk_index": 0,
        "start": 0, "end": len(text), "text": text,
    }
    expected = "RAG Context:\n" + json.dumps([record], ensure_ascii=False)
    budget = len(expected)

    context = rag_context.build_rag_context(hits, max_chars=budget)

    assert context.content == expected
    assert context.sources == [small]
    assert len(context.content) == budget
    empty = rag_context.RagContext("", [])
    assert rag_context.build_rag_context(hits, max_chars=budget - 1) == empty
    assert rag_context.build_rag_context(hits, max_chars=0) == empty
    assert rag_context.build_rag_context([]) == empty
    with pytest.raises(ValueError):
        rag_context.build_rag_context(hits, max_chars=-1)
