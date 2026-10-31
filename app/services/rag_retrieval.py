"""问题检索编排：只嵌入问题，复用已有文档索引，不生成回答。"""

from pathlib import Path

from app.services.embedding import embed_texts
from app.services.rag import RetrievedChunk
from app.services.vector_store import open_notes_collection, query_chunks


async def retrieve(
    question: str,
    persist_directory: Path,
    *,
    top_k: int = 3,
) -> list[RetrievedChunk]:
    """空索引返回[]并跳过嵌入；输入和模型/存储异常继续向上传播。"""
    if not question.strip():
        raise ValueError("Question must not be blank.")

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    collection = open_notes_collection(persist_directory)
    if collection.count() == 0:
        return []

    vectors = await embed_texts([question])

    return query_chunks(
        collection,
        vectors[0],
        top_k=top_k,
    )
