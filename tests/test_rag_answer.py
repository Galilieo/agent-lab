"""fake 检索/Agent 验证上层编排策略；实际执行上下文与引用纯函数。"""

import asyncio

import pytest

from app.services import rag_answer
from app.services.agent import AgentResult
from app.services.llm import LLMResult
from app.services.rag import DocumentChunk, RetrievedChunk
from app.services.rag_context import build_rag_context


def model_call(answer):
    return LLMResult(
        answer=answer, model="fake-model", upstream_status=200, latency_ms=1.0,
        prompt_tokens=20, completion_tokens=10, total_tokens=30,
    )


def test_rag_answer_keeps_repeated_valid_citations_and_marks_invalid_ones(tmp_path, monkeypatch):
    database = DocumentChunk("notes/database.md", 0, 0, 4, "及时关闭")
    unused = DocumentChunk("notes/memory.md", 0, 0, 4, "会话记忆")
    # 这条检索结果因过大被预算排除，正文引用它也应报告无效。
    oversized = DocumentChunk("notes/long.md", 0, 0, 5000, "长" * 5000)
    hits = [RetrievedChunk(oversized, 0.0), RetrievedChunk(database, 0.1), RetrievedChunk(unused, 0.2)]
    raw_answer = (
        "第一段。[notes/database.md::0]\n第二段。[notes/database.md::0]\n"
        "未提供的片段。[notes/long.md::0]\n再次引用它。[notes/long.md::0]"
    )
    call = model_call(raw_answer)
    history = [{"role": "user", "content": "此前问题"}]
    before = [dict(item) for item in history]
    observed = []

    async def fake_retrieve(question, persist_directory, *, top_k):
        observed.append((question, persist_directory, top_k))
        return hits

    async def fake_agent(message, history=None, *, memory_context, rag_context):
        assert message == "当前问题"
        assert history == before
        assert memory_context == "记忆参考"
        assert rag_context == build_rag_context(hits, max_chars=1000).content
        return AgentResult(answer=raw_answer, model_calls=[call])

    monkeypatch.setattr(rag_answer, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag_answer, "run_agent", fake_agent)

    result = asyncio.run(rag_answer.answer_with_rag(
        "当前问题", tmp_path, history, memory_context="记忆参考", top_k=5, max_chars=1000,
    ))

    assert observed == [("当前问题", tmp_path, 5)]
    assert result.answer == (
        "第一段。[notes/database.md::0]\n第二段。[notes/database.md::0]\n"
        "未提供的片段。[引用未找到]\n再次引用它。[引用未找到]\n\n"
        + rag_answer.CITATION_WARNING
    )
    assert result.sources == [database]
    assert result.invalid_ids == ["notes/long.md::0"]
    assert result.model_calls == [call]
    assert result.model_calls[0].answer == raw_answer
    assert history == before


@pytest.mark.parametrize("has_hits,max_chars", [(False, 4000), (True, 0)])
def test_rag_answer_skips_agent_when_no_material_fits(tmp_path, monkeypatch, has_hits, max_chars):
    async def fake_retrieve(question, persist_directory, *, top_k):
        return [RetrievedChunk(DocumentChunk("notes/a.md", 0, 0, 2, "原文"), 0.1)] if has_hits else []

    async def unexpected_agent(*args, **kwargs):
        pytest.fail("没有可用资料时不应调用回答模型")

    monkeypatch.setattr(rag_answer, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag_answer, "run_agent", unexpected_agent)

    result = asyncio.run(rag_answer.answer_with_rag("当前问题", tmp_path, max_chars=max_chars))

    assert result == rag_answer.RagAnswer(rag_answer.NO_MATERIAL_ANSWER, [], [], [])


@pytest.mark.parametrize("stage", ["retrieval", "agent"])
def test_rag_answer_propagates_failures_instead_of_claiming_no_material(tmp_path, monkeypatch, stage):
    failure = RuntimeError("synthetic service failure")

    async def fake_retrieve(*args, **kwargs):
        if stage == "retrieval":
            raise failure
        return [RetrievedChunk(DocumentChunk("notes/a.md", 0, 0, 2, "原文"), 0.1)]

    async def failed_agent(*args, **kwargs):
        raise failure

    monkeypatch.setattr(rag_answer, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag_answer, "run_agent", failed_agent)

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(rag_answer.answer_with_rag("当前问题", tmp_path))
    assert caught.value is failure


def test_rag_answer_preserves_calls_if_agent_returns_no_final_text(tmp_path, monkeypatch):
    call = model_call(None)

    async def fake_retrieve(*args, **kwargs):
        return [RetrievedChunk(DocumentChunk("notes/a.md", 0, 0, 2, "原文"), 0.1)]

    async def empty_agent(*args, **kwargs):
        return AgentResult(answer=None, model_calls=[call])

    monkeypatch.setattr(rag_answer, "retrieve", fake_retrieve)
    monkeypatch.setattr(rag_answer, "run_agent", empty_agent)

    with pytest.raises(rag_answer.RagAnswerError) as caught:
        asyncio.run(rag_answer.answer_with_rag("当前问题", tmp_path))
    assert caught.value.completed_model_calls == [call]
