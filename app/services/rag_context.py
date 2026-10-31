"""把检索片段封装为有字符预算的参考资料，保留对应来源。"""

from dataclasses import dataclass
import json

from app.services.rag import DocumentChunk, RetrievedChunk


@dataclass(frozen=True)
class RagContext:
    """sources 为实际提供给模型的片段，不表示模型已经引用。"""

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
