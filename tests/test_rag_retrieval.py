"""人工向量验证真实 Chroma 检索，fake Embedding，不访问模型。"""

import asyncio

import pytest

from app.services import rag_retrieval
from app.services.rag import DocumentChunk, RetrievedChunk
from app.services.vector_store import open_notes_collection, upsert_chunks


def test_retrieve_embeds_only_question_and_returns_ranked_chunks(tmp_path, monkeypatch):
    collection = open_notes_collection(tmp_path / "chroma")
    chunks = [
        DocumentChunk("notes/database.md", 0, 0, 5, "关闭数据库"),
        DocumentChunk("notes/memory.md", 0, 0, 4, "会话记忆"),
        DocumentChunk("notes/cooking.md", 0, 0, 4, "番茄炒蛋"),
    ]
    query_vector = [1.0] + [0.0] * 1023
    upsert_chunks(collection, chunks, [
        query_vector, [0.0, 1.0] + [0.0] * 1022, [-1.0] + [0.0] * 1023,
    ])
    observed = []

    async def fake_embed_texts(texts):
        observed.append(list(texts))
        return [query_vector]

    monkeypatch.setattr(rag_retrieval, "embed_texts", fake_embed_texts)
    question = "为什么请求模型前释放数据库连接？"

    hits = asyncio.run(rag_retrieval.retrieve(question, tmp_path / "chroma", top_k=2))
    assert hits == [RetrievedChunk(chunks[0], 0.0), RetrievedChunk(chunks[1], 1.0)]

    # TopK 超过库中条数时，返回全部可用片段。
    all_hits = asyncio.run(rag_retrieval.retrieve(question, tmp_path / "chroma", top_k=10))
    assert [hit.chunk for hit in all_hits] == chunks
    assert [hit.distance for hit in all_hits] == pytest.approx([0.0, 1.0, 2.0])
    assert observed == [[question], [question]]
    assert collection.count() == 3


def test_retrieve_handles_empty_invalid_and_failed_embedding(tmp_path, monkeypatch):
    index_dir = tmp_path / "chroma"
    observed = []

    async def failed_embedding(texts):
        observed.append(list(texts))
        raise RuntimeError("Embedding unavailable")

    monkeypatch.setattr(rag_retrieval, "embed_texts", failed_embedding)

    assert asyncio.run(rag_retrieval.retrieve("查询", index_dir)) == []
    with pytest.raises(ValueError):
        asyncio.run(rag_retrieval.retrieve(" \n ", index_dir))
    with pytest.raises(ValueError):
        asyncio.run(rag_retrieval.retrieve("查询", index_dir, top_k=0))
    assert observed == []

    # 有索引时请求嵌入，失败必须传播，不能返回空列表冒充未命中。
    collection = open_notes_collection(index_dir)
    upsert_chunks(
        collection, [DocumentChunk("notes/example.md", 0, 0, 2, "原文")],
        [[1.0] + [0.0] * 1023],
    )
    with pytest.raises(RuntimeError, match="Embedding unavailable"):
        asyncio.run(rag_retrieval.retrieve("查询", index_dir))
    assert observed == [["查询"]]
