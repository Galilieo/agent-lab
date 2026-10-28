"""验证聊天后的记忆写入、失败隔离与回答历史一致性。

fake Agent 与提取器隔离模型；HTTP、SQLite、来源绑定和反馈更新真实执行。
新连接观察提取前及请求后的状态，检查正常回答先提交、最终历史与返回一致。
从学习草稿恢复为正式收集，已用于验证聊天记忆接线的正常与失败路径。
"""

import logging

import pytest
from fastapi.testclient import TestClient

from app.database import create_connection
from app.main import app
from app.schemas import MemoryExtractionResult
from app.services.agent import AgentResult
from app.services.llm import LLMResult


NORMAL_ANSWER = "这是正常回答。"
PRIVATE_MODEL_BODY = "FAKE_PRIVATE_MODEL_BODY"


def read_chat_state(database_path):
    """从独立连接读取本测试数据库，不把未提交内容当成已保存结果。"""
    connection = create_connection(database_path)
    try:
        return {
            "messages": connection.execute(
                "SELECT message_id, role, content FROM message ORDER BY message_id"
            ).fetchall(),
            "model_calls": connection.execute(
                """
                SELECT outcome, response_message_id
                FROM model_call ORDER BY model_call_id
                """
            ).fetchall(),
            "memories": connection.execute(
                """
                SELECT scope, scope_id, key, value, source_message_id
                FROM memory ORDER BY scope, scope_id, key
                """
            ).fetchall(),
        }
    finally:
        connection.close()


@pytest.fixture
def chat_memory_scenario(monkeypatch, tmp_path):
    """提供单次成功 Agent、可切换失败的提取器，以及真实临时数据库客户端。"""
    database_path = str(tmp_path / "chat-memory.sqlite3")
    observed = {"fail_extract": False, "before_extract": None}

    async def fake_run_agent(message, history=None):
        return AgentResult(
            answer=NORMAL_ANSWER,
            model_calls=[
                LLMResult(
                    answer=NORMAL_ANSWER,
                    model="fake-main-model",
                    upstream_status=200,
                    latency_ms=1.0,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                )
            ],
        )

    async def fake_extract_memories(message):
        observed["before_extract"] = read_chat_state(database_path)
        if observed["fail_extract"]:
            # 制造真正的 Pydantic JSON 校验失败，异常详情会含模拟的私有正文。
            return MemoryExtractionResult.model_validate_json(PRIVATE_MODEL_BODY)
        return MemoryExtractionResult.model_validate(
            {
                "action": "upsert",
                "memories": [
                    {"scope": "user", "key": "answer_language", "value": "中文"}
                ],
            }
        )

    monkeypatch.setattr("app.main.settings.database_path", database_path)
    monkeypatch.setattr("app.main.run_agent", fake_run_agent)
    monkeypatch.setattr(
        "app.main.extract_memories", fake_extract_memories, raising=False
    )

    with TestClient(app) as client:
        yield {"client": client, "database_path": database_path, "observed": observed}


def test_chat_saves_memory_and_updates_original_answer(chat_memory_scenario):
    """自动保存成功后，原助手消息与返回内容都含确认，主调用记录保持独立。"""
    scenario = chat_memory_scenario
    message = "以后默认用中文回答。"
    response = scenario["client"].post(
        "/chat",
        json={"conversation_id": "conversation-A", "user_id": "user-001", "message": message},
    )
    state = read_chat_state(scenario["database_path"])
    expected_answer = NORMAL_ANSWER + "\n\n已保存本次记忆。"
    before_extract = scenario["observed"]["before_extract"]

    # 检查 HTTP 200、完整 ChatResponse，以及数据库只有 user / assistant 两条消息。
    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "conversation-A",
        "answer": expected_answer,
    }
    source_id = state["messages"][0][0]
    assistant_id = state["messages"][1][0]
    # 检查记忆绑定真实用户来源，主 model_call 只有一条 succeeded 且关联原助手消息。
    assert state == {
        "messages": [
            (source_id, "user", message),
            (assistant_id, "assistant", expected_answer),
        ],
        "model_calls": [("succeeded", assistant_id)],
        "memories": [
            ("user", "user-001", "answer_language", "中文", source_id),
        ],
    }
    # 检查提取开始前，原正常回答与主调用已经能由另一连接读到。
    assert before_extract == {
        "messages": [
            (source_id, "user", message),
            (assistant_id, "assistant", NORMAL_ANSWER),
        ],
        "model_calls": [("succeeded", assistant_id)],
        "memories": [],
    }


@pytest.mark.parametrize(
    ("message", "expected_answer"),
    [
        ("以后 Python 会取代 Java 吗？", NORMAL_ANSWER),
        ("保存我的回答语言偏好：中文。", NORMAL_ANSWER + "\n\n本次长期记忆未保存。"),
    ],
    ids=["ordinary-extraction-failure", "explicit-save-failure"],
)
def test_chat_isolates_memory_failure(
    chat_memory_scenario, caplog, message, expected_answer
):
    """提取失败仍返回正常聊天；显式请求有失败反馈，日志不泄露私有正文。"""
    scenario = chat_memory_scenario
    scenario["observed"]["fail_extract"] = True

    with caplog.at_level(logging.WARNING, logger="app.main"):
        response = scenario["client"].post(
            "/chat",
            json={"conversation_id": "conversation-A", "user_id": "user-001", "message": message},
        )

    state = read_chat_state(scenario["database_path"])

    # 检查 HTTP 与完整 ChatResponse、最终助手消息一致；失败不留下记忆。
    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "conversation-A",
        "answer": expected_answer,
    }
    # 检查主 model_call 仍只有一条 succeeded，且仍关联原助手消息。
    source_id = state["messages"][0][0]
    assistant_id = state["messages"][1][0]
    assert state == {
        "messages": [
            (source_id, "user", message),
            (assistant_id, "assistant", expected_answer),
        ],
        "model_calls": [("succeeded", assistant_id)],
        "memories": []
    }
    # 日志包含 ValidationError 失败分类，但不包含 PRIVATE_MODEL_BODY。
    assert any(
        record.name == "app.main"
        and "ValidationError" in record.getMessage()
        for record in caplog.records
    )
    assert PRIVATE_MODEL_BODY not in caplog.text
