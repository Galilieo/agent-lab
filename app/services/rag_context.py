"""把检索片段封装为有字符预算的参考资料，保留对应来源。"""

from dataclasses import dataclass
import json

from app.services.rag import DocumentChunk, RetrievedChunk


@dataclass(frozen=True)
class RagContext:
    """content 为准备交给模型的参考，sources 为其中实际装入预算的片段。

    构造对象不代表已发送模型；调用方负责传递，并保留 sources 作引用映射。
    sources 不含因预算跳过的片段，也不表示模型已经引用其中全部资料。
    """

    content: str
    sources: list[DocumentChunk]


def build_rag_context(
    hits: list[RetrievedChunk],
    *,
    max_chars: int = 4000,
) -> RagContext:
    """按检索顺序整片选择，计入完整渲染开销，不修改输入。"""
    if max_chars < 0:
        raise ValueError("max_chars must be non-negative.")

    records = []
    sources = []
    content = ""

    for hit in hits:
        chunk = hit.chunk
        record = {
            "id": f"{chunk.source}::{chunk.chunk_index}",
            "source": chunk.source,
            "chunk_index": chunk.chunk_index,
            "start": chunk.start,
            "end": chunk.end,
            "text": chunk.text,
        }

        candidate = records + [record]
        candidate_content = (
            "RAG Context:\n"
            + json.dumps(candidate, ensure_ascii=False)
        )

        if len(candidate_content) > max_chars:
            continue

        records = candidate
        sources.append(chunk)
        content = candidate_content

    return RagContext(content=content, sources=sources)
