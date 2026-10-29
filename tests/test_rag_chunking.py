"""验证切分、重叠和原文出处；不读取真实笔记或调用模型。"""

from app.services import rag


def test_split_document_preserves_overlap_and_source_without_duplicate_tail():
    text = "abcdefghij"
    chunks = rag.split_document(
        text, source="notes/example.md", chunk_size=6, overlap=2,
    )

    assert chunks == [
        rag.DocumentChunk("notes/example.md", 0, 0, 6, "abcdef"),
        rag.DocumentChunk("notes/example.md", 1, 4, 10, "efghij"),
    ]
    assert all(chunk.text == text[chunk.start:chunk.end] for chunk in chunks)
