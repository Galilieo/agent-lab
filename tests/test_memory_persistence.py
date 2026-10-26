"""用临时文件 SQLite 验证批量记忆提交与中途失败回滚。

准备连接先提交并关闭，持久化函数与结果查询各用自己的连接，检查实际落库结果。
不调用模型或真实业务数据库；此处不验证 HTTP 层的聊天失败隔离。
"""

import pytest

from app import database
from app.services import memory


INITIAL_TIMESTAMP = "2026-10-24T10:00:00+00:00"
WRITE_TIMESTAMP = "2026-10-24T10:01:00+00:00"


@pytest.fixture
def memory_database(tmp_path):
    """准备已提交的两个用户来源和一条助手回答，返回路径及真实消息 ID。"""
    database_path = str(tmp_path / "memory.sqlite3")
    connection = database.create_connection(database_path)
    try:
        database.initialize_schema(connection)
        database.upsert_conversation(
            connection, "conversation-A", INITIAL_TIMESTAMP, user_id="user-001"
        )
        database.upsert_conversation(
            connection, "conversation-other", INITIAL_TIMESTAMP, user_id="user-002"
        )
        source_id = database.insert_user_message(
            connection, "conversation-A", "以后默认中文，本会话练习英文。", INITIAL_TIMESTAMP
        )
        other_source_id = database.insert_user_message(
            connection, "conversation-other", "这是其他用户的消息。", INITIAL_TIMESTAMP
        )
        database.insert_assistant_message(
            connection, "conversation-A", "这是一条已经保存的正常回答。", INITIAL_TIMESTAMP
        )
        connection.commit()
    finally:
        connection.close()

    return {
        "database_path": database_path,
        "source_id": source_id,
        "other_source_id": other_source_id,
    }


def read_database_state(database_path):
    """用新连接查询记忆和消息，避免把同一事务内可见误当成已经提交。"""
    connection = database.create_connection(database_path)
    try:
        return {
            "memories": connection.execute(
                """
                SELECT scope, scope_id, key, value, source_message_id, updated_at
                FROM memory
                ORDER BY scope, scope_id, key
                """
            ).fetchall(),
            "messages": connection.execute(
                """
                SELECT message_id, conversation_id, role, content
                FROM message
                ORDER BY message_id
                """
            ).fetchall(),
        }
    finally:
        connection.close()


def test_persist_memory_writes_commits_whole_batch(memory_database):
    """两条合法记忆应完整提交，并能通过另一连接读取全部字段。"""
    database_path = memory_database["database_path"]
    source_id = memory_database["source_id"]
    writes = [
        memory.MemoryWrite("user", "user-001", "answer_language", "中文", source_id),
        memory.MemoryWrite(
            "conversation", "conversation-A", "answer_language", "英文", source_id
        ),
    ]

    memory.persist_memory_writes(
        writes,
        database_path=database_path,
        updated_at=WRITE_TIMESTAMP,
    )

    actual = read_database_state(database_path)["memories"]
    expected = [
        ("conversation", "conversation-A", "answer_language", "英文", source_id, WRITE_TIMESTAMP),
        ("user", "user-001", "answer_language", "中文", source_id, WRITE_TIMESTAMP),
    ]

    # 新连接读回完整字段，保护两条记忆都已提交，而非仅在原连接中可见。
    assert actual == expected


def test_persist_memory_writes_rolls_back_earlier_update(memory_database):
    """第二条来源无效时，第一条更新也应撤销，已有消息与旧记忆保持不变。"""
    database_path = memory_database["database_path"]
    source_id = memory_database["source_id"]

    # 旧值与消息在本批记忆事务开始前已提交，失败不应删除或改变它们。
    connection = database.create_connection(database_path)
    try:
        database.upsert_memory(
            connection,
            scope="user",
            scope_id="user-001",
            key="answer_language",
            value="中文",
            source_message_id=source_id,
            updated_at=INITIAL_TIMESTAMP,
        )
        connection.commit()
    finally:
        connection.close()

    before = read_database_state(database_path)
    writes = [
        memory.MemoryWrite("user", "user-001", "answer_language", "英文", source_id),
        # 故意使用另一用户的真实消息 ID，触发已有的数据库来源归属检查。
        memory.MemoryWrite(
            "conversation",
            "conversation-A",
            "explanation_style",
            "详细讲解",
            memory_database["other_source_id"],
        ),
    ]

    def persist_invalid_batch():
        memory.persist_memory_writes(
            writes,
            database_path=database_path,
            updated_at=WRITE_TIMESTAMP,
        )

    # 来源拒绝必须报告给调用方，不能吞掉异常后伪装成整批成功。
    with pytest.raises(ValueError):
        persist_invalid_batch()

    after = read_database_state(database_path)

    # 回滚恢复旧记忆全部字段，同时保留本批事务开始前已提交的消息。
    assert after == before
