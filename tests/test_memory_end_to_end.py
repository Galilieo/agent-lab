"""跨会话保存、改口更新与隔离的离线串联验收。

只 fake 模型 HTTP，真实执行提取器、Pydantic、来源绑定、SQLite 和 Prompt 接线。
预设模型输出不证明真实模型提取准确性或语言遵循性。
"""

import json

import httpx
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.services.memory import MEMORY_EXTRACTION_PROMPT, extract_memories


SAVE_CHINESE = "记住：以后默认用中文回答；仅本会话先讲原理。"
CHANGE_ENGLISH = "请保存修改：以后默认用英文回答。"
QUESTION = "你好，介绍一下你自己。"
ANSWER = "这是预设的正常回答。"


def test_memory_survives_new_conversations_and_updates_with_new_source(
    monkeypatch, tmp_path,
):
    """防止新会话只依赖历史、改口仅新增不更新、来源不变或用户记忆泄漏。"""
    database_path = str(tmp_path / "memory-end-to-end.sqlite3")
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
                observed["extract"].append(json)
                current = messages[-1]["content"]
                if current == SAVE_CHINESE:
                    candidates = [
                        {"scope": "user", "key": "answer_language", "value": "中文"},
                        {"scope": "conversation", "key": "explanation_style", "value": "先讲原理"},
                    ]
                elif current == CHANGE_ENGLISH:
                    candidates = [
                        {"scope": "user", "key": "answer_language", "value": "英文"},
                    ]
                else:
                    raise AssertionError("Unexpected extraction request")
                # 用模块 json 生成模型正文，后续由真实提取器与 Pydantic 解析。
                content = encode_extraction(candidates)
            else:
                observed["chat"].append(json)
                content = ANSWER
            return httpx.Response(
                200, request=httpx.Request("POST", url),
                json={"choices": [{"message": {"role": "assistant", "content": content}}]},
            )

    monkeypatch.setattr("app.main.settings.database_path", database_path)
    monkeypatch.setattr("app.services.llm.settings.openai_base_url", "https://model.invalid/v1")
    monkeypatch.setattr("app.services.llm.settings.openai_api_key", "fake-test-key")
    monkeypatch.setattr("app.services.llm.httpx.AsyncClient", FakeModelClient)
    # 覆盖 conftest 默认 skip：提取调用也必须通过真实 service 和 fake HTTP。
    monkeypatch.setattr("app.main.extract_memories", extract_memories)

    def send(client, conversation_id, user_id, message):
        response = client.post("/chat", json={
            "conversation_id": conversation_id, "user_id": user_id, "message": message,
        })
        assert response.status_code == 200
        return response.json()["answer"]

    def read_user_memory():
        # 独立连接观察已经提交的值和真实来源，不读进程里的临时变量。
        connection = database.create_connection(database_path)
        try:
            return connection.execute(
                """
                SELECT m.memory_id, m.value, m.source_message_id,
                       s.conversation_id, s.role, s.content
                FROM memory m JOIN message s ON s.message_id = m.source_message_id
                WHERE m.scope = 'user' AND m.scope_id = 'user-001'
                    AND m.key = 'answer_language'
                """
            ).fetchall()
        finally:
            connection.close()

    with TestClient(app) as client:
        assert send(client, "A", "user-001", SAVE_CHINESE) == ANSWER + "\n\n已保存本次记忆。"
        original = read_user_memory()
        assert len(original) == 1
        assert original[0][1] == "中文"
        assert original[0][3:] == ("A", "user", SAVE_CHINESE)

        assert send(client, "B", "user-001", QUESTION) == ANSWER
        assert send(client, "B", "user-001", CHANGE_ENGLISH) == ANSWER + "\n\n已保存本次记忆。"
        updated = read_user_memory()
        assert len(updated) == 1
        assert updated[0][0] == original[0][0]  # 更新同一条记忆，不重复插入。
        assert updated[0][1] == "英文"
        assert updated[0][2] != original[0][2]
        assert updated[0][3:] == ("B", "user", CHANGE_ENGLISH)

        assert send(client, "C", "user-001", QUESTION) == ANSWER
        assert send(client, "D", "user-other", QUESTION) == ANSWER

    assert len(observed["chat"]) == 5
    assert len(observed["extract"]) == 2
    a, b, update_b, c, other = [p["messages"] for p in observed["chat"]]
    # A 保存前没有记忆；B/C 的新会话没有旧历史，偏好来自真实 memory 表。
    assert a[1:] == [{"role": "user", "content": SAVE_CHINESE}]
    for messages, language in [(b, "中文"), (c, "英文")]:
        assert len(messages) == 3
        assert messages[1]["role"] == "user"
        label, body = messages[1]["content"].split("\n", 1)
        assert label == "Memory Context:"
        assert json.loads(body) == {"answer_language": language}
        assert messages[2] == {"role": "user", "content": QUESTION}
    # 改口这轮调用前还是旧默认；真实更新在正常回答提交后发生。
    assert update_b[1] == b[1]
    assert update_b[2:] == [
        {"role": "user", "content": QUESTION},
        {"role": "assistant", "content": ANSWER},
        {"role": "user", "content": CHANGE_ENGLISH},
    ]
    assert other[1:] == [{"role": "user", "content": QUESTION}]

    for payload, question in zip(observed["extract"], [SAVE_CHINESE, CHANGE_ENGLISH]):
        assert payload["messages"] == [
            {"role": "system", "content": MEMORY_EXTRACTION_PROMPT},
            {"role": "user", "content": question},
        ]
        assert "tools" not in payload

    connection = database.create_connection(database_path)
    try:
        # A 的会话级风格保留在 A，不跨会话泄漏；改口不会删除它。
        assert connection.execute(
            "SELECT scope, scope_id, key, value FROM memory ORDER BY scope, key"
        ).fetchall() == [
            ("conversation", "A", "explanation_style", "先讲原理"),
            ("user", "user-001", "answer_language", "英文"),
        ]
        # 两次提取不混入五次主 Agent 的成功调用记录。
        assert connection.execute(
            "SELECT outcome FROM model_call ORDER BY model_call_id"
        ).fetchall() == [("succeeded",)] * 5
        stored = connection.execute(
            "SELECT role, content FROM message WHERE conversation_id = 'B' ORDER BY message_id"
        ).fetchall()
        assert stored == [
            ("user", QUESTION), ("assistant", ANSWER),
            ("user", CHANGE_ENGLISH), ("assistant", ANSWER + "\n\n已保存本次记忆。"),
        ]
    finally:
        connection.close()


def encode_extraction(candidates):
    """避免 fake post 的 json 请求体参数遮蔽模块；只生成外部响应。"""
    return json.dumps({"action": "upsert", "memories": candidates}, ensure_ascii=False)
