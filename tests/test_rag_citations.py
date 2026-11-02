"""验证本轮来源白名单与引用报告；不调用模型，不验证语义支持。"""

from app.services import rag_citations
from app.services.rag import DocumentChunk


def test_citation_check_reports_valid_and_unknown_ids_in_first_appearance_order():
    database = DocumentChunk("notes/database.md", 0, 0, 4, "及时关闭")
    memory = DocumentChunk("notes/memory.md", 1, 8, 12, "会话记忆")
    unused = DocumentChunk("notes/unused.md", 0, 0, 4, "未被引用")
    sources = [database, memory, unused]
    before = list(sources)
    answer = (
        "先谈记忆。[notes/memory.md::1]"
        "一个未提供的来源。[notes/missing.md::0]"
        "再谈数据库。[notes/database.md::0]"
        "重复合法引用。[notes/memory.md::1]"
        "同一文件的未提供片段。[notes/database.md::99]"
        "重复无效引用。[notes/missing.md::0]"
    )

    result = rag_citations.check_citations(answer, sources)

    assert result.valid_sources == [memory, database]
    assert result.invalid_ids == ["notes/missing.md::0", "notes/database.md::99"]
    assert sources == before


def test_citation_check_handles_no_citations_and_empty_available_sources():
    answer = "现有资料没有说明；普通编号 [1] 和 [示例] 不属于约定的 RAG 引用。"

    result = rag_citations.check_citations(answer, [])

    assert result == rag_citations.CitationCheck(valid_sources=[], invalid_ids=[])
    # 空来源列表也要检查已经出现的引用，不能直接认定为没有引用问题。
    missing = rag_citations.check_citations("见 [notes/database.md::0]。", [])
    assert missing.valid_sources == []
    assert missing.invalid_ids == ["notes/database.md::0"]
