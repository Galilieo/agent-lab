"""本地 BGE-M3 嵌入探索：一批文本、向量检查和余弦排序。

在项目根目录运行 .venv/bin/python playground/rag_embedding_probe.py。
仅访问本机 Ollama，使用合成示例，不调用 DeepSeek、不下载模型。
这是 RAG 前置探索，不是生产检索器或模型质量评测。
"""

import asyncio
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


MODEL = "bge-m3:latest"
QUERY = "为什么请求模型前要释放数据库连接？"
DOCUMENTS = [
    "调用大模型之前，应先提交数据库事务并关闭连接，避免网络等待期间长时间占用事务。",
    "用户级记忆可跨会话复用，会话级记忆只在当前会话内生效。",
    "番茄炒蛋的做法是先炒鸡蛋，再加入番茄翻炒。",
]
RESULT_PATH = Path(__file__).resolve().parent / "results" / "bge_m3_probe.json"


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """用原生 Python 计算夹角余弦，保留完整范数计算以展示机制。"""
    dot = math.fsum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(math.fsum(value * value for value in left))
    right_norm = math.sqrt(math.fsum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        raise ValueError("Cannot compare zero-length vectors.")
    return dot / (left_norm * right_norm)


async def main() -> None:
    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
        response = await client.post(
            "http://127.0.0.1:11434/api/embed",
            json={"model": MODEL, "input": [QUERY, *DOCUMENTS], "truncate": False},
        )
        response.raise_for_status()
        payload = response.json()

    vectors = payload["embeddings"]
    if len(vectors) != 1 + len(DOCUMENTS):
        raise ValueError("Embedding count does not match input count.")
    for vector in vectors:
        if len(vector) != 1024 or not all(math.isfinite(value) for value in vector):
            raise ValueError("Expected finite 1024-dimensional BGE-M3 vectors.")

    query_vector = vectors[0]
    ranking = sorted(
        [
            {"document": document, "cosine_similarity": cosine_similarity(query_vector, vector)}
            for document, vector in zip(DOCUMENTS, vectors[1:], strict=True)
        ],
        key=lambda item: item["cosine_similarity"],
        reverse=True,
    )
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "model": payload["model"],
        "query": QUERY,
        "vector_count": len(vectors),
        "dimensions": [len(vector) for vector in vectors],
        "l2_norms": [math.sqrt(math.fsum(x * x for x in vector)) for vector in vectors],
        "query_vector_first_five_values": query_vector[:5],
        "ranking": ranking,
        "elapsed_seconds": time.perf_counter() - started,
        "prompt_eval_count": payload.get("prompt_eval_count"),
        "scope": "One synthetic Chinese query; local embedding probe only, not a retrieval benchmark.",
    }
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Result saved to {RESULT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
