"""fake 模型和检索验证原生循环；真实执行工具适配、预算与计算器。"""

import asyncio
import json

import pytest

from app.services import agent, rag_tools
from app.services.llm import LLMResult, LLMToolCall
from app.services.rag import DocumentChunk, RetrievedChunk
from app.tools import AVAILABLE_TOOLS


def reply(answer=None, calls=None):
    return LLMResult(
        answer=answer, model="fake-model", upstream_status=200, latency_ms=1.0,
        prompt_tokens=None, completion_tokens=None, total_tokens=None,
        tool_calls=calls or [],
    )


def knowledge_call(call_id, query):
    return LLMToolCall(call_id, "search_knowledge", json.dumps({"query": query}))


def test_agent_delivers_multiple_searches_and_retains_each_rounds_sources(tmp_path, monkeypatch):
    first = DocumentChunk("notes/database.md", 0, 0, 4, "及时关闭")
    second = DocumentChunk("notes/memory.md", 1, 10, 14, "会话记忆")
    large = DocumentChunk("notes/large.md", 0, 0, 5000, "长" * 5000)
    queries = []
    observed = []
    history = [{"role": "user", "content": "此前问题"}]
    final_answer = "事务应及时结束。[notes/database.md::0]记忆按范围生效。[notes/memory.md::1]结果5。"

    async def fake_retrieve(question, persist_directory, *, top_k):
        assert persist_directory == tmp_path
        queries.append(question)
        return ([RetrievedChunk(large, 0.0), RetrievedChunk(first, 0.1)]
                if question == "事务" else [RetrievedChunk(second, 0.2)])

    async def fake_model(message, history=None, tools=None, additional_messages=None, **kwargs):
        assert message == "查资料并算2+3"
        assert history == [{"role": "user", "content": "此前问题"}]
        assert kwargs["memory_context"] == "记忆参考"
        assert kwargs["rag_context"] == ""
        assert "search_knowledge" in [tool["function"]["name"] for tool in tools]
        observed.append([dict(item) for item in additional_messages])
        if len(observed) == 1:
            return reply(calls=[knowledge_call("search-1", "事务")])
        if len(observed) == 2:
            return reply(calls=[
                knowledge_call("search-2", "记忆"),
                LLMToolCall("calc-1", "calculator", '{"left":2,"operator":"+","right":3}'),
            ])
        assert len(observed) == 3
        return reply(final_answer)

    monkeypatch.setattr(rag_tools, "retrieve", fake_retrieve)
    monkeypatch.setattr(agent, "generate_reply", fake_model)

    result = asyncio.run(agent.run_agent(
        "查资料并算2+3", history, memory_context="记忆参考", knowledge_directory=tmp_path,
    ))

    assert queries == ["事务", "记忆"]
    assert result.answer == final_answer
    assert len(result.model_calls) == 3
    assert result.knowledge_sources == [first, second]
    assert observed[0] == []
    tool_messages = [item for item in observed[2] if item["role"] == "tool"]
    assert [item["tool_call_id"] for item in tool_messages] == ["search-1", "search-2", "calc-1"]
    for item, expected_id in zip(tool_messages[:2], ["notes/database.md::0", "notes/memory.md::1"], strict=True):
        label, body = item["content"].split("\n", 1)
        assert label == "RAG Context:"
        assert [record["id"] for record in json.loads(body)] == [expected_id]
    assert tool_messages[2]["content"] == "5"
    assert observed[2][:2] == observed[1]
    assert history == [{"role": "user", "content": "此前问题"}]
    assert "search_knowledge" not in [tool["function"]["name"] for tool in AVAILABLE_TOOLS]


@pytest.mark.parametrize("search", [False, True], ids=["direct-answer", "empty-search"])
def test_agent_can_answer_without_search_and_continue_after_empty_search(tmp_path, monkeypatch, search):
    model_calls = []
    queries = []

    async def empty_retrieve(question, persist_directory, *, top_k):
        queries.append(question)
        return []

    async def fake_model(message, tools=None, additional_messages=None, **kwargs):
        model_calls.append(list(additional_messages))
        if search and len(model_calls) == 1:
            return reply(calls=[knowledge_call("empty-1", "没有资料")])
        return reply("资料未包含答案。" if search else "你好。")

    monkeypatch.setattr(rag_tools, "retrieve", empty_retrieve)
    monkeypatch.setattr(agent, "generate_reply", fake_model)

    result = asyncio.run(agent.run_agent("问题", knowledge_directory=tmp_path))

    assert result.answer == ("资料未包含答案。" if search else "你好。")
    assert result.knowledge_sources == []
    assert len(result.model_calls) == (2 if search else 1)
    assert queries == (["没有资料"] if search else [])
    if search:
        tool_message = model_calls[1][-1]
        assert tool_message["role"] == "tool"
        assert tool_message["tool_call_id"] == "empty-1"
        assert "未检索到可用片段" in tool_message["content"]


@pytest.mark.parametrize("enabled", [False, True], ids=["tool-disabled", "retrieval-failed"])
def test_agent_keeps_successful_model_call_when_knowledge_execution_fails(tmp_path, monkeypatch, enabled):
    failure = RuntimeError("synthetic retrieval failure")
    queries = []
    call = reply(calls=[knowledge_call("failure-1", "查询")])

    async def failed_retrieve(question, persist_directory, *, top_k):
        queries.append(question)
        raise failure

    async def fake_model(message, tools=None, **kwargs):
        names = [tool["function"]["name"] for tool in tools]
        assert ("search_knowledge" in names) is enabled
        return call

    monkeypatch.setattr(rag_tools, "retrieve", failed_retrieve)
    monkeypatch.setattr(agent, "generate_reply", fake_model)

    with pytest.raises(agent.AgentToolError) as caught:
        asyncio.run(agent.run_agent("问题", knowledge_directory=tmp_path if enabled else None))

    assert caught.value.completed_model_calls == [call]
    assert queries == (["查询"] if enabled else [])
    if enabled:
        assert caught.value.cause is failure
    else:
        assert isinstance(caught.value.cause, ValueError)
