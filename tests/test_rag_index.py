"""真实临时笔记与 Chroma，fake Embedding；不会调用 Ollama 或聊天 API。"""

import asyncio

import pytest

from app.services import rag_index
from app.services.rag import DocumentChunk
from app.services.vector_store import open_notes_collection, upsert_chunks


def test_build_index_syncs_changed_deleted_and_empty_notes(tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    index_dir = tmp_path / "chroma"
    first = notes_dir / "a.md"
    removed = notes_dir / "b.md"
    first.write_text("abcdef", encoding="utf-8")
    removed.write_text("ghi", encoding="utf-8")
    observed = []

    async def fake_embed_texts(texts):
        assert texts  # 空目录应跳过嵌入，不必发空批次。
        observed.append(list(texts))
        return [[1.0] + [0.0] * 1023 for _ in texts]

    monkeypatch.setattr(rag_index, "embed_texts", fake_embed_texts)

    assert asyncio.run(rag_index.build_index(
        notes_dir, index_dir, chunk_size=3, overlap=0,
    )) == 3

    # a 缩短、b 删除、c 新增：不能遗留 a 的第二片或 b 的旧内容。
    first.write_text("XYZ", encoding="utf-8")
    removed.unlink()
    added = notes_dir / "c.md"
    added.write_text("jkl", encoding="utf-8")
    assert asyncio.run(rag_index.build_index(
        notes_dir, index_dir, chunk_size=3, overlap=0,
    )) == 2

    collection = open_notes_collection(index_dir)
    rows = collection.get(include=["documents"])
    assert dict(zip(rows["ids"], rows["documents"], strict=True)) == {
        "notes/a.md::0": "XYZ",
        "notes/c.md::0": "jkl",
    }

    first.unlink()
    added.unlink()
    assert asyncio.run(rag_index.build_index(
        notes_dir, index_dir, chunk_size=3, overlap=0,
    )) == 0
    assert collection.count() == 0
    assert observed == [["abc", "def", "ghi"], ["XYZ", "jkl"]]


def test_build_index_keeps_previous_records_when_embedding_fails(tmp_path, monkeypatch):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "new.md").write_text("新资料", encoding="utf-8")
    index_dir = tmp_path / "chroma"
    collection = open_notes_collection(index_dir)
    upsert_chunks(
        collection,
        [DocumentChunk("notes/old.md", 0, 0, 3, "旧资料")],
        [[1.0] + [0.0] * 1023],
    )
    before = collection.get(include=["documents", "metadatas"])

    async def failed_embedding(texts):
        raise RuntimeError("Embedding unavailable")

    monkeypatch.setattr(rag_index, "embed_texts", failed_embedding)

    with pytest.raises(RuntimeError, match="Embedding unavailable"):
        asyncio.run(rag_index.build_index(notes_dir, index_dir))

    assert collection.get(include=["documents", "metadatas"]) == before
