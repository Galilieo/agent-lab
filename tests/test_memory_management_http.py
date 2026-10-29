"""HTTP 管理及删除后聊天串联；真实临时库，只 fake 外部模型 HTTP。"""

import json as json_module
import logging
import sqlite3

import httpx
import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.services.memory import MEMORY_EXTRACTION_PROMPT, extract_memories


SAVE = "记住：以后默认用中文回答。"
QUESTION = "你好。"
FOLLOW_UP = "以后 Python 还值得学习吗？"
ANSWER = "这是测试回答。"
IDENTITY = {"conversation_id": "A", "user_id": "user-001"}
DELETE = {**IDENTITY, "key": "answer_language", "target": "all"}


@pytest.fixture
def management_http_scenario(monkeypatch, tmp_path):
    path = str(tmp_path / "management-http.sqlite3")
    observed = {"chat": [], "extract": []}

    class FakeModelClient:
        def __init__(self, *, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, *, headers, json):
            messages = json["messages"]
            if messages[0]["content"] == MEMORY_EXTRACTION_PROMPT:
                observed["extract"].append(messages)
                current = messages[-1]["content"]
                if current == SAVE:
                    result = {"action": "upsert", "memories": [
                        {"scope": "user", "key": "answer_language", "value": "中文"},
                    ]}
                elif current == FOLLOW_UP:
                    result = {"action": "skip", "memories": []}
                else:
                    raise AssertionError("Unexpected extraction input")
                content = json_module.dumps(result, ensure_ascii=False)
            else:
                observed["chat"].append(messages)
                content = ANSWER
            return httpx.Response(
                200, request=httpx.Request("POST", url),
                json={"choices": [{"message": {"role": "assistant", "content": content}}]},
            )

    monkeypatch.setattr("app.main.settings.database_path", path)
    monkeypatch.setattr("app.services.llm.settings.openai_base_url", "https://model.invalid/v1")
    monkeypatch.setattr("app.services.llm.settings.openai_api_key", "fake-test-key")
    monkeypatch.setattr("app.services.llm.httpx.AsyncClient", FakeModelClient)
    monkeypatch.setattr("app.main.extract_memories", extract_memories)
    with TestClient(app) as client:
        yield {"client": client, "path": path, "observed": observed}


def send_chat(scenario, message, conversation_id="A", user_id="user-001"):
    response = scenario["client"].post("/chat", json={
        "conversation_id": conversation_id, "user_id": user_id, "message": message,
    })
    assert response.status_code == 200
    return response


def stored_memories(scenario):
    connection = database.create_connection(scenario["path"])
    try:
        return connection.execute(
            "SELECT scope, scope_id, key, value FROM memory ORDER BY memory_id"
        ).fetchall()
    finally:
        connection.close()


def test_http_delete_stops_injection_without_reextracting_old_history(management_http_scenario):
    scenario = management_http_scenario
    client = scenario["client"]
    send_chat(scenario, SAVE)
    query = client.post("/memories/query", json=IDENTITY)
    assert query.status_code == 200
    records = query.json()["memories"]
    assert len(records) == 1
    assert records[0] == {
        "scope": "user", "scope_id": "user-001", "key": "answer_language", "value": "中文",
        "source_message_id": 1, "updated_at": records[0]["updated_at"],
    }
    assert records[0]["updated_at"]

    response = client.post("/memories/delete", json=DELETE)
    assert response.status_code == 200
    assert response.json() == {"deleted_count": 1}
    assert stored_memories(scenario) == []  # 新连接证明删除已提交。
    assert client.post("/memories/delete", json=DELETE).json() == {"deleted_count": 0}
    assert client.post("/memories/query", json=IDENTITY).json() == {"memories": []}

    # 旧保存消息还在 A 的 history 中；本次“以后”问题仍会触发真实提取流程。
    send_chat(scenario, FOLLOW_UP)
    messages = scenario["observed"]["chat"][-1]
    assert {"role": "user", "content": SAVE} in messages
    assert not any(m["content"].startswith("Memory Context:") for m in messages)
    assert scenario["observed"]["extract"][-1] == [
        {"role": "system", "content": MEMORY_EXTRACTION_PROMPT},
        {"role": "user", "content": FOLLOW_UP},
    ]
    assert stored_memories(scenario) == []

    send_chat(scenario, QUESTION, conversation_id="B")
    assert scenario["observed"]["chat"][-1][1:] == [{"role": "user", "content": QUESTION}]
    send_chat(scenario, SAVE)
    send_chat(scenario, QUESTION, conversation_id="C")
    restored = scenario["observed"]["chat"][-1][1]
    assert restored["content"].startswith("Memory Context:\n")
    assert json_module.loads(restored["content"].split("\n", 1)[1]) == {"answer_language": "中文"}
    assert stored_memories(scenario) == [("user", "user-001", "answer_language", "中文")]
    assert len(scenario["observed"]["chat"]) == 5
    assert len(scenario["observed"]["extract"]) == 3


def test_http_management_rejects_wrong_owner_and_invalid_inputs(management_http_scenario):
    scenario = management_http_scenario
    client = scenario["client"]
    send_chat(scenario, SAVE)
    before = stored_memories(scenario)
    for endpoint, body in [("query", IDENTITY), ("delete", DELETE)]:
        assert client.post(
            f"/memories/{endpoint}", json={**body, "user_id": "user-other"},
        ).status_code == 409
        assert client.post(
            f"/memories/{endpoint}", json={**body, "conversation_id": "missing"},
        ).status_code == 400
    for change in [{"target": "invalid"}, {"key": "unknown"}, {"scope_id": "user-other"}]:
        assert client.post("/memories/delete", json={**DELETE, **change}).status_code == 422
    # 匿名允许管理自己的会话；全用户范围删除须有用户 ID。
    send_chat(scenario, QUESTION, conversation_id="anonymous", user_id=None)
    assert client.post("/memories/query", json={"conversation_id": "anonymous"}).json() == {"memories": []}
    assert client.post("/memories/delete", json={
        "conversation_id": "anonymous", "key": "answer_language", "target": "all",
    }).status_code == 422
    assert stored_memories(scenario) == before
    assert len(scenario["observed"]["chat"]) == 2


def test_http_management_preserves_chat_identity_without_trimming(management_http_scenario):
    """带空格的 ID 和不带空格的 ID 必须保持为 /chat 已保存的两组不同归属。"""
    scenario = management_http_scenario
    client = scenario["client"]
    send_chat(scenario, SAVE)
    send_chat(scenario, SAVE, conversation_id=" A ", user_id=" user-001 ")
    padded_identity = {"conversation_id": " A ", "user_id": " user-001 "}
    response = client.post("/memories/query", json=padded_identity)
    assert response.status_code == 200
    assert [r["scope_id"] for r in response.json()["memories"]] == [" user-001 "]
    deleted = client.post("/memories/delete", json={
        **padded_identity, "key": "answer_language", "target": "all",
    })
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted_count": 1}
    assert stored_memories(scenario) == [("user", "user-001", "answer_language", "中文")]


def test_http_delete_commit_failure_rolls_back_and_returns_failure(
    management_http_scenario, monkeypatch, caplog,
):
    scenario = management_http_scenario
    send_chat(scenario, SAVE)
    before = stored_memories(scenario)
    closed = []
    private_error = "PRIVATE_COMMIT_ERROR"

    class CommitFailureConnection:
        def __init__(self, path):
            self.real = database.create_connection(path)

        def execute(self, *args, **kwargs):
            return self.real.execute(*args, **kwargs)

        def commit(self):
            raise sqlite3.OperationalError(private_error)

        def rollback(self):
            self.real.rollback()

        def close(self):
            closed.append(True)
            self.real.close()

    monkeypatch.setattr("app.main.create_connection", CommitFailureConnection)
    with caplog.at_level(logging.WARNING, logger="app.main"):
        response = scenario["client"].post("/memories/delete", json=DELETE)
    assert response.status_code == 503
    assert response.json() == {"detail": "Memory storage is unavailable."}
    assert stored_memories(scenario) == before
    assert closed == [True]
    assert any("OperationalError" in record.getMessage() for record in caplog.records)
    assert private_error not in caplog.text
