"""以真实临时 Chroma 验证框架检索适配，问题嵌入使用 fake。

人工向量决定检索顺序，原生 retrieve、存储查询和 Document 转换真实执行。
不请求 Ollama/聊天模型；这些结果不证明真实语义检索质量。
"""

import asyncio

import pytest
from langchain_core.documents import Document

from app.services import langchain_retrieval, rag_retrieval
from app.services.rag import DocumentChunk
from app.services.vector_store import open_notes_collection, upsert_chunks


@pytest.fixture(autouse=True)
def disable_retriever_tracing(monkeypatch):
    """临时关闭外部追踪，保持检索测试离线。"""
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")


def test_retriever_preserves_document_content_provenance_and_ranking(
    tmp_path, monkeypatch
):
    """包装后的查询保留片段原文、ID、位置和排序，继续复用已有索引。"""
    index_dir = tmp_path / "chroma"
    collection = open_notes_collection(index_dir)
    chunks = [
        DocumentChunk("notes/a.md", 1, 4, 11, "原文甲\r\n继续"),
        DocumentChunk("notes/b.md", 2, 10, 13, "原文乙"),
    ]
    query_vector = [1.0] + [0.0] * 1023
    upsert_chunks(collection, chunks, [
        query_vector,
        [0.0, 1.0] + [0.0] * 1022,
    ])
    observed = []

    async def fake_embedding(texts):
        observed.append(list(texts))
        return [query_vector]

    monkeypatch.setattr(rag_retrieval, "embed_texts", fake_embedding)
    retriever = langchain_retrieval.build_notes_retriever(index_dir, top_k=2)
    question = "原文甲在哪里？"

    documents = asyncio.run(retriever.ainvoke(question))

    assert all(isinstance(document, Document) for document in documents)
    assert [(document.id, document.page_content, document.metadata)
            for document in documents] == [
        ("notes/a.md::1", "原文甲\r\n继续", {
            "source": "notes/a.md", "chunk_index": 1,
            "start": 4, "end": 11, "distance": 0.0,
        }),
        ("notes/b.md::2", "原文乙", {
            "source": "notes/b.md", "chunk_index": 2,
            "start": 10, "end": 13, "distance": 1.0,
        }),
    ]
    assert observed == [[question]]
    assert collection.count() == 2


def test_retriever_keeps_empty_index_distinct_from_embedding_failure(
    tmp_path, monkeypatch
):
    """空库正常返回[]；有资料时嵌入故障继续抛出，不能冒充未命中。"""
    index_dir = tmp_path / "chroma"
    observed = []

    async def failed_embedding(texts):
        observed.append(list(texts))
        raise RuntimeError("Embedding unavailable")

    monkeypatch.setattr(rag_retrieval, "embed_texts", failed_embedding)
    retriever = langchain_retrieval.build_notes_retriever(index_dir, top_k=2)

    assert asyncio.run(retriever.ainvoke("查询")) == []
    assert observed == []

    collection = open_notes_collection(index_dir)
    upsert_chunks(collection, [DocumentChunk("notes/a.md", 0, 0, 2, "原文")], [
        [1.0] + [0.0] * 1023,
    ])
    with pytest.raises(RuntimeError, match="Embedding unavailable"):
        asyncio.run(retriever.ainvoke("查询"))
    assert observed == [["查询"]]
