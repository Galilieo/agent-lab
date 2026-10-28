"""验证会话归属冲突先于消息写入和 Agent 调用被拒绝。

从没有 user_id 列的旧 SQLite 表启动，同时检查旧库兼容和创建时间保留。
Agent 被 fake 替换，因此只验证请求链和持久化，不调用真实模型。
"""

import pytest
from fastapi.testclient import TestClient

from app.database import create_connection
from app.main import app
from app.services.agent import AgentResult
from app.services.llm import LLMResult


@pytest.fixture
def ownership_scenario(monkeypatch, tmp_path):
    """准备旧版会话数据库、fake Agent 与启动后的 TestClient，并记录 Agent 调用。"""
    database_file = tmp_path / "legacy-agent-lab.db"
    connection = create_connection(str(database_file))
    try:
        # 模拟升级前已存在的会话表，刻意不包含 user_id。
        connection.execute(
            """
            CREATE TABLE conversation (
                conversation_id TEXT PRIMARY KEY NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO conversation
                (conversation_id, status, created_at, updated_at)
            VALUES (?, 'active', ?, ?)
            """,
            (
                "legacy-001",
                "2026-08-01T00:00:00+00:00",
                "2026-08-01T00:00:00+00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    calls = []

    async def fake_run_agent(message, history=None, *, memory_context=""):
        calls.append({"message": message, "history": history})
        return AgentResult(
            answer="模拟回答",
            model_calls=[
                LLMResult(
                    answer="模拟回答",
                    model="fake-model",
                    upstream_status=200,
                    latency_ms=1.0,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                )
            ],
        )

    monkeypatch.setattr("app.main.settings.database_path", str(database_file))
    monkeypatch.setattr("app.main.run_agent", fake_run_agent)

    with TestClient(app) as client:
        yield {"client": client, "calls": calls, "database_file": database_file}


@pytest.mark.parametrize(
    ("owner_id", "conflicting_id"),
    [
        ("user-001", "user-002"),
        ("user-001", None),
        (None, "user-001"),
    ],
    ids=["different-user", "omitted-user", "claim-anonymous"],
)
def test_chat_keeps_conversation_owner_and_rejects_conflicts(
    ownership_scenario,
    owner_id,
    conflicting_id,
):
    """验证换用户、省略已绑定用户和认领匿名会话均失败，旧数据与消息数量保持正确。"""
    client = ownership_scenario["client"]
    payload = {"conversation_id": "owned-001", "message": "第一条消息"}
    if owner_id is not None:
        payload["user_id"] = owner_id
    first = client.post("/chat", json=payload)

    payload["message"] = "同一归属继续聊天"
    repeated = client.post("/chat", json=payload)

    conflict_payload = {
        "conversation_id": "owned-001",
        "message": "这条不应保存",
    }
    if conflicting_id is not None:
        conflict_payload["user_id"] = conflicting_id
    conflicting = client.post("/chat", json=conflict_payload)

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert conflicting.status_code == 409
    assert len(ownership_scenario["calls"]) == 2

    connection = create_connection(str(ownership_scenario["database_file"]))
    try:
        stored_owner = connection.execute(
            "SELECT user_id FROM conversation WHERE conversation_id = ?",
            ("owned-001",),
        ).fetchone()[0]
        message_count = connection.execute(
            "SELECT COUNT(*) FROM message WHERE conversation_id = ?",
            ("owned-001",),
        ).fetchone()[0]
        legacy = connection.execute(
            "SELECT user_id, created_at FROM conversation WHERE conversation_id = ?",
            ("legacy-001",),
        ).fetchone()
    finally:
        connection.close()

    assert stored_owner == owner_id
    assert message_count == 4
    assert legacy == (
        None,
        "2026-08-01T00:00:00+00:00",
    )
