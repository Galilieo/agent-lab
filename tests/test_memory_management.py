"""记忆管理数据库契约：只看当前可见记录，按归属和明确目标删除。

真实内存 SQLite；不运行模型、不删除真实库，提交由调用方负责。
"""

import pytest

from app import database
from app.services.memory import merge_memories


TIMESTAMP = "2026-10-28T10:00:00+00:00"


@pytest.fixture
def management_database():
    connection = database.create_connection()
    try:
        database.initialize_schema(connection)
        sources = {}
        for conversation_id, user_id in [("A", "user-001"), ("B", "user-001"),
                                         ("other", "user-other"), ("anonymous", None)]:
            database.upsert_conversation(
                connection, conversation_id, TIMESTAMP, user_id=user_id,
            )
            sources[conversation_id] = database.insert_user_message(
                connection, conversation_id, "测试来源。", TIMESTAMP,
            )
        for scope, scope_id, key, value, source in [
            ("user", "user-001", "answer_language", "中文", "A"),
            ("conversation", "A", "answer_language", "英文", "A"),
            ("conversation", "B", "answer_language", "日文", "B"),
            ("user", "user-001", "tech_stack", "Python", "A"),
            ("user", "user-other", "answer_language", "德文", "other"),
            ("conversation", "other", "answer_language", "德文", "other"),
            ("conversation", "anonymous", "answer_language", "中文", "anonymous"),
        ]:
            database.upsert_memory(
                connection, scope=scope, scope_id=scope_id, key=key, value=value,
                source_message_id=sources[source], updated_at=TIMESTAMP,
            )
        connection.commit()
        yield connection, sources
    finally:
        connection.close()


def test_list_and_delete_memory_records_preserves_explicit_scope(management_database):
    """查看保留两层原记录；局部删除恢复默认，跨范围删除只清当前用户同 key。"""
    connection, sources = management_database
    original_messages = connection.execute("SELECT * FROM message ORDER BY message_id").fetchall()
    records = database.list_memory_records(
        connection, user_id="user-001", conversation_id="A",
    )
    assert sorted(records, key=lambda r: (r["scope"], r["key"])) == [
        {"scope": "conversation", "scope_id": "A", "key": "answer_language", "value": "英文",
         "source_message_id": sources["A"], "updated_at": TIMESTAMP},
        {"scope": "user", "scope_id": "user-001", "key": "answer_language", "value": "中文",
         "source_message_id": sources["A"], "updated_at": TIMESTAMP},
        {"scope": "user", "scope_id": "user-001", "key": "tech_stack", "value": "Python",
         "source_message_id": sources["A"], "updated_at": TIMESTAMP},
    ]

    assert database.delete_memory_records(
        connection, user_id="user-001", conversation_id="A",
        key="answer_language", target="conversation",
    ) == 1
    assert merge_memories(database.load_memories(
        connection, user_id="user-001", conversation_id="A",
    )) == {"answer_language": "中文", "tech_stack": "Python"}
    # 重复删除同一目标是零条，不当成第二次实际删除。
    assert database.delete_memory_records(
        connection, user_id="user-001", conversation_id="A",
        key="answer_language", target="conversation",
    ) == 0
    connection.rollback()  # 数据库函数不擅自提交；调用方可撤回本次局部删除。
    assert len(database.load_memories(
        connection, user_id="user-001", conversation_id="A",
    )) == 3

    assert database.delete_memory_records(
        connection, user_id="user-001", conversation_id="A",
        key="answer_language", target="all",
    ) == 3
    connection.commit()
    assert connection.execute(
        "SELECT scope, scope_id, key, value FROM memory ORDER BY scope, scope_id, key"
    ).fetchall() == [
        ("conversation", "anonymous", "answer_language", "中文"),
        ("conversation", "other", "answer_language", "德文"),
        ("user", "user-001", "tech_stack", "Python"),
        ("user", "user-other", "answer_language", "德文"),
    ]
    assert database.delete_memory_records(
        connection, user_id="user-001", conversation_id="A", key="tech_stack", target="user",
    ) == 1
    connection.rollback()
    assert connection.execute("SELECT * FROM message ORDER BY message_id").fetchall() == original_messages


def test_memory_management_rejects_owner_conflict_and_anonymous_global_delete(management_database):
    """归属冲突不能查看/删除；匿名只能操作当前匿名会话，不能清除全部匿名会话。"""
    connection, sources = management_database
    before = connection.execute("SELECT * FROM memory ORDER BY memory_id").fetchall()
    with pytest.raises(database.ConversationOwnershipError):
        database.list_memory_records(connection, user_id="user-other", conversation_id="A")
    with pytest.raises(database.ConversationOwnershipError):
        database.delete_memory_records(
            connection, user_id="user-other", conversation_id="A",
            key="answer_language", target="all",
        )
    for target in ("user", "all"):
        with pytest.raises(ValueError):
            database.delete_memory_records(
                connection, user_id=None, conversation_id="anonymous",
                key="answer_language", target=target,
            )
    with pytest.raises(ValueError):
        database.delete_memory_records(
            connection, user_id="user-001", conversation_id="A",
            key="answer_language", target="invalid",
        )
    assert connection.execute("SELECT * FROM memory ORDER BY memory_id").fetchall() == before
    assert database.list_memory_records(
        connection, user_id=None, conversation_id="anonymous",
    ) == [{
        "scope": "conversation", "scope_id": "anonymous", "key": "answer_language", "value": "中文",
        "source_message_id": sources["anonymous"], "updated_at": TIMESTAMP,
    }]
    assert database.delete_memory_records(
        connection, user_id=None, conversation_id="anonymous",
        key="answer_language", target="conversation",
    ) == 1
