"""本地 BGE-M3 文本嵌入；只负责文本到向量，不保存索引或调用聊天模型。"""

import math

import httpx


EMBEDDING_URL = "http://127.0.0.1:11434/api/embed"
EMBEDDING_MODEL = "bge-m3:latest"
EMBEDDING_DIMENSIONS = 1024


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """返回按输入顺序对应的向量；空输入不请求服务，失败不伪装成空结果。"""
    if not texts:
        return []

    async with httpx.AsyncClient(
        timeout=120.0,
        trust_env=False,
    ) as client:
        response = await client.post(
            EMBEDDING_URL,
            json={
                "model": EMBEDDING_MODEL,
                "input": texts,
                "truncate": False,
            },
        )
        response.raise_for_status()
        payload = response.json()

        vectors = payload["embeddings"]

        if len(vectors) != len(texts):
            raise ValueError("Embedding count does not match input count.")

        for vector in vectors:
            if (
                len(vector) != EMBEDDING_DIMENSIONS
                or not all(math.isfinite(value) for value in vector)
            ):
                raise ValueError("Expected finite 1024-dimensional vectors.")

        return vectors
