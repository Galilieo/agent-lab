"""本地 Chroma 向量存储；显式接收已有向量，不生成 Embedding。"""

from pathlib import Path

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings

from app.services.rag import DocumentChunk, RetrievedChunk


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


def sync_chunks(
    collection: Collection,
    chunks: list[DocumentChunk],
    vectors: list[list[float]],
) -> None:
    """将专用笔记集合与当前片段同步；先 upsert，成功后删除多余 ID。

    空片段列表表示清空此集合。不提供跨 upsert/delete 的事务或并发快照。
    """
    existing_ids = set(collection.get(include=[])["ids"])

    current_ids = {
        f"{chunk.source}::{chunk.chunk_index}"
        for chunk in chunks
    }

    upsert_chunks(collection, chunks, vectors)

    obsolete_ids = existing_ids - current_ids
    if obsolete_ids:
        collection.delete(ids=sorted(obsolete_ids))


def query_chunks(
    collection: Collection,
    query_vector: list[float],
    *,
    top_k: int = 3,
) -> list[RetrievedChunk]:
    """检索一条问题向量，返回原文、出处和距离；不进行相关性阈值过滤。"""
    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    limit = min(top_k, collection.count())
    if limit == 0:
        return []

    result = collection.query(
        query_embeddings=[query_vector],
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for text, metadata, distance in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
        strict=True,
    ):
        chunk = DocumentChunk(
            source=metadata["source"],
            chunk_index=metadata["chunk_index"],
            start=metadata["start"],
            end=metadata["end"],
            text=text,
        )
        hits.append(
            RetrievedChunk(chunk=chunk, distance=distance)
        )

    return hits
