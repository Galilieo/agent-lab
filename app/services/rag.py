"""原生 RAG 的文档片段与字符切分；不调用模型。"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentChunk:
    """保留原文与出处；start/end 为原始文本中左闭右开的字符位置。"""

    source: str
    chunk_index: int
    start: int
    end: int
    text: str


def split_document(
    text: str,
    *,
    source: str,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[DocumentChunk]:
    """按字符窗口切分；保留原文，到达文末后停止，不重复生成末尾片段。"""
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("需要 chunk_size > 0，且 0 <= overlap < chunk_size")

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))

        chunks.append(
            DocumentChunk(
                source=source,
                chunk_index=len(chunks),
                start=start,
                end=end,
                text=text[start:end],
            )
        )

        if end == len(text):
            break

        start = end - overlap

    return chunks


def load_markdown_chunks(
    notes_dir: Path,
    *,
    chunk_size: int = 500,
    overlap: int = 80,
) -> list[DocumentChunk]:
    """读取指定笔记目录的普通 Markdown 并切分，不递归或跟随符号链接。

    source 采用目录名/文件名；当前用于单一笔记目录。
    """
    if not notes_dir.is_dir():
        raise FileNotFoundError("Notes directory does not exist")

    chunks = []

    for note_file in sorted(notes_dir.glob("*.md")):
        if note_file.is_symlink() or not note_file.is_file():
            continue

        # 保留 CRLF 等原始换行，确保字符位置与原文一致。
        with note_file.open(encoding="utf-8", newline="") as stream:
            text = stream.read()

        file_chunks = split_document(
            text,
            source=f"{notes_dir.name}/{note_file.name}",
            chunk_size=chunk_size,
            overlap=overlap,
        )
        chunks.extend(file_chunks)

    return chunks
