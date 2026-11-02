"""验证按需工具来源的回答收尾；纯 Python，不调用模型或检索。"""

from app.services import rag_answer
from app.services.agent import AgentResult
from app.services.llm import LLMResult
from app.services.rag import DocumentChunk


def model_call(answer):
    return LLMResult(
        answer=answer, model="fake-model", upstream_status=200, latency_ms=1.0,
        prompt_tokens=None, completion_tokens=None, total_tokens=None,
    )


def test_finalization_uses_delivered_tool_sources_without_changing_agent_result():
    first = DocumentChunk("notes/database.md", 0, 0, 4, "及时关闭")
    second = DocumentChunk("notes/memory.md", 0, 0, 4, "会话记忆")
    unused = DocumentChunk("notes/unused.md", 0, 0, 4, "没有引用")
    delivered = [first, second, first, unused]
    raw_answer = (
        "记忆。[notes/memory.md::0]事务。[notes/database.md::0]"
        "再次引用。[notes/memory.md::0]未知片段。[notes/missing.md::0]"
    )
    call = model_call(raw_answer)
    original = AgentResult(raw_answer, [call], knowledge_sources=delivered)

    result = rag_answer.finalize_rag_answer(original, original.knowledge_sources)

    assert result.answer == (
        "记忆。[notes/memory.md::0]事务。[notes/database.md::0]"
        "再次引用。[notes/memory.md::0]未知片段。[引用未找到]\n\n"
        + rag_answer.CITATION_WARNING
    )
    assert result.sources == [second, first]
    assert result.invalid_ids == ["notes/missing.md::0"]
    assert result.model_calls == [call]
    assert original.answer == call.answer == raw_answer
    assert original.knowledge_sources == [first, second, first, unused]


def test_finalization_preserves_direct_answer_when_agent_did_not_search():
    raw_answer = "你好，可以直接聊天。"
    call = model_call(raw_answer)
    original = AgentResult(raw_answer, [call])

    result = rag_answer.finalize_rag_answer(original, original.knowledge_sources)

    # 没检索不等于严格路径的资料缺失；保留真实模型回答及调用，不生成固定兜底。
    assert result == rag_answer.RagAnswer(raw_answer, [], [], [call])
