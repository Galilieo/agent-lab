"""用临时笔记验证读取与切分，不访问模型或项目真实笔记。"""

from app.services import rag


def test_load_markdown_chunks_preserves_text_and_source_and_skips_non_notes(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    # 故意先创建 b，检查结果仍按文件名排列。
    (notes_dir / "b.md").write_text("会话记忆。\n", encoding="utf-8")
    (notes_dir / "a.md").write_text("数据库事务。\n", encoding="utf-8")
    (notes_dir / "ignore.txt").write_text("不是 Markdown", encoding="utf-8")
    (notes_dir / "folder.md").mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("符号链接目标不应读取", encoding="utf-8")
    (notes_dir / "linked.md").symlink_to(outside)

    chunks = rag.load_markdown_chunks(notes_dir)

    assert chunks == [
        rag.DocumentChunk("notes/a.md", 0, 0, 7, "数据库事务。\n"),
        rag.DocumentChunk("notes/b.md", 0, 0, 6, "会话记忆。\n"),
    ]


def test_load_markdown_chunks_preserves_crlf_and_original_character_offsets(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    original = "a\r\nb\r\nc"
    (notes_dir / "windows.md").write_bytes(original.encode("utf-8"))

    chunks = rag.load_markdown_chunks(notes_dir, chunk_size=3, overlap=1)

    assert chunks == [
        rag.DocumentChunk("notes/windows.md", 0, 0, 3, "a\r\n"),
        rag.DocumentChunk("notes/windows.md", 1, 2, 5, "\nb\r"),
        rag.DocumentChunk("notes/windows.md", 2, 4, 7, "\r\nc"),
    ]
    assert all(chunk.text == original[chunk.start:chunk.end] for chunk in chunks)
