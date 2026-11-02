"""真实 HTTP/SQLite/Chroma 与原生 Agent；只替换模型 HTTP 和问题嵌入。"""

import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from app import database, main
from app.services import rag_retrieval
from app.services.rag import DocumentChunk
from app.services.rag_answer import CITATION_WARNING
from app.services.vector_store import open_notes_collection, upsert_chunks


QUERY_VECTOR = [1.0] + [0.0] * 1023


@pytest.fixture
def chat_knowledge_scenario(tmp_path, monkeypatch):
    database_path = str(tmp_path / "chat.sqlite3")
    index_dir = tmp_path / "chroma"
    # 只替换路由配置，不读取或输出真实环境变量/密钥。
    config = SimpleNamespace(database_path=database_path, rag_index_path=str(index_dir))
    replies = []
    payloads = []
    embeddings = []
    embedding_error = []

    async def fake_embed(texts):
        embeddings.append(list(texts))
        if embedding_error:
            raise embedding_error[0]
        return [QUERY_VECTOR]

    class FakeModelClient:
        def __init__(self, *, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, headers, json):
            payloads.append(json)
            assert len(payloads) <= len(replies), "发生未预期的模型调用"
            return httpx.Response(
                200, request=httpx.Request("POST", url),
                json={"choices": [{"message": replies[len(payloads) - 1]}]},
            )

    monkeypatch.setattr(main, "settings", config)
    monkeypatch.setattr("app.services.llm.settings.openai_base_url", "https://model.invalid/v1")
    monkeypatch.setattr("app.services.llm.settings.openai_api_key", "fake-test-key")
    monkeypatch.setattr("app.services.llm.httpx.AsyncClient", FakeModelClient)
    monkeypatch.setattr(rag_retrieval, "embed_texts", fake_embed)

    with TestClient(main.app, raise_server_exceptions=False) as client:
        yield SimpleNamespace(
            client=client, database_path=database_path, index_dir=index_dir, config=config,
            replies=replies, payloads=payloads, embeddings=embeddings, embedding_error=embedding_error,
        )


def request_search(query="释放连接"):
    return {"role": "assistant", "content": None, "tool_calls": [{
        "id": "knowledge-http-1", "type": "function",
        "function": {"name": "search_knowledge", "arguments": json.dumps({"query": query})},
    }]}


def read_saved(scenario):
    connection = database.create_connection(scenario.database_path)
    try:
        messages = connection.execute("SELECT role, content FROM message ORDER BY message_id").fetchall()
        calls = connection.execute(
            "SELECT outcome, response_message_id FROM model_call ORDER BY model_call_id"
        ).fetchall()
        return messages, calls
    finally:
        connection.close()


def populate(scenario):
    text = "请求模型前提交事务并关闭连接。"
    chunk = DocumentChunk("notes/database.md", 0, 0, len(text), text)
    unused = DocumentChunk("notes/other.md", 0, 0, 4, "其他资料")
    collection = open_notes_collection(scenario.index_dir)
    upsert_chunks(collection, [chunk, unused], [QUERY_VECTOR, [0.0, 1.0] + [0.0] * 1022])
    return chunk


def test_chat_delivers_knowledge_and_saves_final_answer_before_returning_sources(chat_knowledge_scenario):
    s = chat_knowledge_scenario
    chunk = populate(s)
    raw_answer = "及时结束事务。[notes/database.md::0]重复引用。[notes/database.md::0]未知。[notes/missing.md::0]"
    final_answer = (
        "及时结束事务。[notes/database.md::0]重复引用。[notes/database.md::0]未知。[引用未找到]\n\n"
        + CITATION_WARNING
    )
    s.replies.extend([request_search(), {"role": "assistant", "content": raw_answer}])

    response = s.client.post("/chat", json={
        "conversation_id": "knowledge-1", "user_id": "owner", "message": "为什么释放连接？",
    })

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "knowledge-1", "answer": final_answer,
        "sources": [{
            "id": "notes/database.md::0", "source": chunk.source, "chunk_index": 0,
            "start": 0, "end": len(chunk.text), "text": chunk.text,
        }],
        "invalid_citation_ids": ["notes/missing.md::0"],
    }
    assert s.embeddings == [["释放连接"]]
    assert len(s.payloads) == 2
    assert "search_knowledge" in [t["function"]["name"] for t in s.payloads[0]["tools"]]
    assert not any(m.get("role") == "tool" for m in s.payloads[0]["messages"])
    tool_message = s.payloads[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "knowledge-http-1"
    assert tool_message["content"].startswith("RAG Context:\n")
    saved_messages, saved_calls = read_saved(s)
    assert saved_messages == [("user", "为什么释放连接？"), ("assistant", final_answer)]
    assert saved_calls == [("succeeded", None), ("succeeded", 2)]

    # 归属检查先于新消息、检索与模型副作用，不依靠模型判断权限。
    blocked = s.client.post("/chat", json={
        "conversation_id": "knowledge-1", "user_id": "other", "message": "不能查询",
    })
    assert blocked.status_code == 409
    assert len(s.payloads) == 2
    assert s.embeddings == [["释放连接"]]
    assert read_saved(s) == (saved_messages, saved_calls)


@pytest.mark.parametrize("search", [False, True], ids=["direct-answer", "empty-index"])
def test_chat_preserves_direct_answer_and_continues_after_empty_retrieval(chat_knowledge_scenario, search):
    s = chat_knowledge_scenario
    answer = "没有可用资料，暂时无法确认。" if search else "你好。"
    if search:
        s.replies.append(request_search())
    s.replies.append({"role": "assistant", "content": answer})

    response = s.client.post("/chat", json={"conversation_id": "no-material", "message": "你好"})

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "no-material", "answer": answer,
        "sources": [], "invalid_citation_ids": [],
    }
    assert s.embeddings == []
    assert len(s.payloads) == (2 if search else 1)
    if search:
        assert "未检索到可用片段" in s.payloads[1]["messages"][-1]["content"]
    assert read_saved(s)[0] == [("user", "你好"), ("assistant", answer)]


@pytest.mark.parametrize("failure", ["embedding", "empty-answer"])
def test_chat_reports_knowledge_failures_without_losing_successful_model_calls(chat_knowledge_scenario, failure):
    s = chat_knowledge_scenario
    if failure == "embedding":
        populate(s)
        s.embedding_error.append(RuntimeError("synthetic embedding failure"))
        s.replies.append(request_search())
        detail = "Agent tool execution failed."
    else:
        s.replies.append({"role": "assistant", "content": None})
        detail = "RAG Agent returned no usable final answer."

    response = s.client.post("/chat", json={"conversation_id": "failed", "message": "查询"})

    assert response.status_code == 502
    assert response.json() == {"detail": detail}
    assert len(s.payloads) == 1
    assert s.embeddings == ([["释放连接"]] if failure == "embedding" else [])
    assert read_saved(s) == ([("user", "查询")], [("succeeded", None)])


def test_chat_without_configured_index_does_not_offer_knowledge_tool(chat_knowledge_scenario):
    s = chat_knowledge_scenario
    s.config.rag_index_path = None
    s.replies.append({"role": "assistant", "content": "普通回答"})

    response = s.client.post("/chat", json={"conversation_id": "disabled", "message": "你好"})

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "disabled", "answer": "普通回答",
        "sources": [], "invalid_citation_ids": [],
    }
    assert [t["function"]["name"] for t in s.payloads[0]["tools"]] == [
        "calculator", "get_current_time", "search_notes",
    ]
    assert s.embeddings == []
