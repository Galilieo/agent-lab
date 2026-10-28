"""验证回答前记忆注入、工具循环复用与读取失败回退。

只替换外部模型 HTTP；路由、临时 SQLite、记忆选择与计算器真实执行。
模型回答是预设的，不作为真实模型遵循偏好优先级的证据。
"""

import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app


TIMESTAMP = "2026-10-28T10:00:00+00:00"
QUESTION = "请用英文告诉我 2 加 3 的结果"
ANSWER = "Two plus three is five."
OLD_USER = "这是之前的一条测试消息。"
OLD_ASSISTANT = "之前的回复。"


@pytest.fixture
def memory_context_scenario(monkeypatch, tmp_path):
    """准备已有会话和记忆，并让模型先调用计算器再返回最终回答。"""
    database_path = str(tmp_path / "memory-context.sqlite3")
    payloads = []

    class FakeModelClient:
        def __init__(self, *, timeout=None):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, *, headers, json):
            payloads.append(json)
            if len(payloads) == 1:
                message = {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_memory_calc",
                        "type": "function",
                        "function": {
                            "name": "calculator",
                            "arguments": '{"left":2,"operator":"+","right":3}',
                        },
                    }],
                }
            elif len(payloads) == 2:
                message = {"role": "assistant", "content": ANSWER}
            else:
                raise AssertionError("Expected two model calls")
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={"choices": [{"message": message}]},
            )

    monkeypatch.setattr("app.main.settings.database_path", database_path)
    monkeypatch.setattr("app.services.llm.settings.openai_base_url", "https://model.invalid/v1")
    monkeypatch.setattr("app.services.llm.settings.openai_api_key", "fake-test-key")
    monkeypatch.setattr("app.services.llm.httpx.AsyncClient", FakeModelClient)

    with TestClient(app) as client:
        connection = database.create_connection(database_path)
        try:
            database.upsert_conversation(
                connection, "conversation-A", TIMESTAMP, user_id="user-001",
            )
            source_id = database.insert_user_message(
                connection, "conversation-A", OLD_USER, TIMESTAMP,
            )
            database.insert_assistant_message(
                connection, "conversation-A", OLD_ASSISTANT, TIMESTAMP,
            )
            for scope, scope_id, key, value in [
                ("user", "user-001", "answer_language", "中文"),
                ("conversation", "conversation-A", "explanation_style", "先讲原理"),
                ("user", "user-001", "learning_goal", "掌握 FastAPI"),
            ]:
                database.upsert_memory(
                    connection, scope=scope, scope_id=scope_id, key=key,
                    value=value, source_message_id=source_id, updated_at=TIMESTAMP,
                )
            connection.commit()
        finally:
            connection.close()
        yield {"client": client, "database_path": database_path, "payloads": payloads}


def send_question(scenario):
    return scenario["client"].post("/chat", json={
        "conversation_id": "conversation-A", "user_id": "user-001", "message": QUESTION,
    })


def read_saved_chat(scenario):
    connection = database.create_connection(scenario["database_path"])
    try:
        messages = connection.execute(
            "SELECT role, content FROM message ORDER BY message_id"
        ).fetchall()
        calls = connection.execute(
            "SELECT outcome FROM model_call ORDER BY model_call_id"
        ).fetchall()
        return messages, calls
    finally:
        connection.close()


def test_chat_injects_memory_once_in_each_model_request(memory_context_scenario):
    """防止路由漏读、循环第二次丢记忆、上下文重复或参考文本写进聊天历史。"""
    scenario = memory_context_scenario
    response = send_question(scenario)
    assert response.status_code == 200
    assert response.json()["answer"] == ANSWER
    assert len(scenario["payloads"]) == 2

    for payload in scenario["payloads"]:
        messages = payload["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"].startswith("Memory Context:\n")
        label, body = messages[1]["content"].split("\n", 1)
        assert label == "Memory Context:"
        assert json.loads(body) == {
            "answer_language": "中文", "explanation_style": "先讲原理",
        }
        # 检查关键使用规则进入实际请求；不把预设英文回答算成模型遵循证据。
        assert "当前用户明确要求优先于历史默认偏好" in messages[0]["content"]
        assert messages[2:5] == [
            {"role": "user", "content": OLD_USER},
            {"role": "assistant", "content": OLD_ASSISTANT},
            {"role": "user", "content": QUESTION},
        ]
        assert sum(m.get("content") == QUESTION for m in messages) == 1
        assert sum(m.get("content", "").startswith("Memory Context:")
                   for m in messages if isinstance(m.get("content"), str)) == 1

    assert len(scenario["payloads"][0]["messages"]) == 5
    tool_request, tool_result = scenario["payloads"][1]["messages"][5:]
    assert tool_request["tool_calls"][0]["id"] == tool_result["tool_call_id"]
    assert tool_result["role"] == "tool"
    assert float(tool_result["content"]) == 5
    assert read_saved_chat(scenario) == (
        [("user", OLD_USER), ("assistant", OLD_ASSISTANT),
         ("user", QUESTION), ("assistant", ANSWER)],
        [("succeeded",), ("succeeded",)],
    )


def test_chat_continues_without_memory_on_sqlite_read_error(
    memory_context_scenario, caplog,
):
    """真实临时库缺少 memory 表时，记录读取错误并保留正常聊天与工具链。"""
    scenario = memory_context_scenario
    connection = database.create_connection(scenario["database_path"])
    try:
        # 仅破坏本测试的临时记忆表，聊天、来源消息与调用记录表保留。
        connection.execute("DROP TABLE memory")
        connection.commit()
    finally:
        connection.close()

    with caplog.at_level(logging.WARNING, logger="app.main"):
        response = send_question(scenario)

    assert response.status_code == 200
    assert response.json()["answer"] == ANSWER
    assert len(scenario["payloads"]) == 2
    assert any(
        record.name == "app.main"
        and "phase=read" in record.getMessage()
        and "OperationalError" in record.getMessage()
        for record in caplog.records
    )
    for payload in scenario["payloads"]:
        assert payload["messages"][1:4] == [
            {"role": "user", "content": OLD_USER},
            {"role": "assistant", "content": OLD_ASSISTANT},
            {"role": "user", "content": QUESTION},
        ]
    assert read_saved_chat(scenario) == (
        [("user", OLD_USER), ("assistant", OLD_ASSISTANT),
         ("user", QUESTION), ("assistant", ANSWER)],
        [("succeeded",), ("succeeded",)],
    )
