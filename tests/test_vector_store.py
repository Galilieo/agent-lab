"""真实临时 Chroma 的入库与跨进程读取；向量为人工数据，不调用模型。"""

import subprocess
import sys

import pytest

from app.services import vector_store
from app.services.rag import DocumentChunk


def test_chroma_retains_chunks_after_writer_process_exits(tmp_path):
    # 在独立进程中写入再退出，主测试进程随后重新打开同一磁盘目录。
    writer = """
import sys
from pathlib import Path
from app.services.rag import DocumentChunk
from app.services.vector_store import open_notes_collection, upsert_chunks

collection = open_notes_collection(Path(sys.argv[1]))
chunks = [
    DocumentChunk('notes/database.md', 0, 0, 5, '关闭数据库'),
    DocumentChunk('notes/memory.md', 0, 0, 4, '会话记忆'),
]
vectors = [[1.0] + [0.0] * 1023, [0.0, 1.0] + [0.0] * 1022]
upsert_chunks(collection, chunks, vectors)
upsert_chunks(collection, chunks, vectors)
assert collection.count() == 2
"""
    completed = subprocess.run(
        [sys.executable, "-c", writer, str(tmp_path / "chroma")],
        capture_output=True, text=True, timeout=45,
    )
    assert completed.returncode == 0, completed.stderr

    collection = vector_store.open_notes_collection(tmp_path / "chroma")
    result = collection.query(
        query_embeddings=[[1.0] + [0.0] * 1023],
        n_results=2,
        include=["documents", "metadatas", "distances"],
    )

    assert collection.count() == 2
    assert result["ids"] == [["notes/database.md::0", "notes/memory.md::0"]]
    assert result["documents"] == [["关闭数据库", "会话记忆"]]
    assert result["metadatas"][0][0] == {
        "source": "notes/database.md", "chunk_index": 0, "start": 0, "end": 5,
    }
    assert result["distances"][0] == pytest.approx([0.0, 1.0])


def test_upsert_chunks_rejects_count_mismatch_before_writing(tmp_path):
    collection = vector_store.open_notes_collection(tmp_path / "chroma")
    chunks = [DocumentChunk("notes/example.md", 0, 0, 2, "原文")]

    with pytest.raises(ValueError, match="count"):
        vector_store.upsert_chunks(collection, chunks, [])

    assert collection.count() == 0
