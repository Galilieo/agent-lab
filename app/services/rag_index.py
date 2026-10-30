"""笔记索引编排：先准备整批向量，再修改专用 Chroma 集合。"""

from pathlib import Path

from app.services.embedding import embed_texts
from app.services.rag import load_markdown_chunks
from app.services.vector_store import open_notes_collection, sync_chunks


async def build_index(
    notes_dir: Path,
    persist_directory: Path,
    *,
    chunk_size: int = 500,
    overlap: int = 80,
) -> int:
    """显式全量同步笔记索引，成功返回当前片段数；错误继续向上传播。"""
    chunks = load_markdown_chunks(
        notes_dir,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    vectors = []
    if chunks:
        vectors = await embed_texts(
            [chunk.text for chunk in chunks]
        )

    collection = open_notes_collection(persist_directory)
    sync_chunks(collection, chunks, vectors)

    return len(chunks)
