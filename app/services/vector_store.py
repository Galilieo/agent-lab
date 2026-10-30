"""本地 Chroma 向量存储；显式接收已有向量，不生成 Embedding。"""

from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings

from app.services.rag import DocumentChunk


COLLECTION_NAME = "notes-bge-m3-1024-v1"


def open_notes_collection(persist_directory: Path) -> Collection:
    """打开本地持久化集合，禁用内置嵌入函数，采用 cosine 距离。"""
    client = chromadb.PersistentClient(
        path=str(persist_directory),
        settings=Settings(anonymized_telemetry=False),
    )

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
    )


def upsert_chunks(
    collection: Collection,
    chunks: list[DocumentChunk],
    vectors: list[list[float]],
) -> None:
    """按 source/片段编号写入原文、出处和向量；不删除已消失的旧片段。"""
    if len(chunks) != len(vectors):
        raise ValueError("Chunk/vector count mismatch.")

    if not chunks:
        return

    collection.upsert(
        ids=[
            f"{chunk.source}::{chunk.chunk_index}"
            for chunk in chunks
        ],
        embeddings=vectors,
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
                "start": chunk.start,
                "end": chunk.end,
            }
            for chunk in chunks
        ],
    )
