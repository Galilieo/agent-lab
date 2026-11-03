"""将原生异步检索适配为 LangChain Document 与 Runnable。

复用既有问题嵌入和 Chroma 索引，保留片段 ID、原文位置及距离。
检索组件使用 ainvoke，不生成回答、重建索引或改写引用策略。
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from app.services.rag_retrieval import retrieve


async def retrieve_documents(
    question: str,
    persist_directory: Path,
    *,
    top_k: int = 3,
) -> list[Document]:
    """检索并转换片段，按原顺序返回；空结果与异常沿用原生契约。"""
    hits = await retrieve(
        question,
        persist_directory,
        top_k=top_k,
    )

    documents = []

    for hit in hits:
        chunk = hit.chunk
        documents.append(Document(
            id=f"{chunk.source}::{chunk.chunk_index}",
            page_content=chunk.text,
            metadata={
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
                "start": chunk.start,
                "end": chunk.end,
                "distance": hit.distance,
            },
        ))

    return documents


def build_notes_retriever(
    persist_directory: Path,
    *,
    top_k: int = 3,
) -> RunnableLambda:
    """绑定应用指定的目录与 TopK，返回接收问题字符串的异步 Runnable。

    创建组件时不检索；ainvoke 时才调用原生检索。
    这是 Runnable 检索适配器，不是 BaseRetriever 子类。
    """
    async def search(question: str) -> list[Document]:
        return await retrieve_documents(
            question,
            persist_directory,
            top_k=top_k,
        )

    return RunnableLambda(search)
