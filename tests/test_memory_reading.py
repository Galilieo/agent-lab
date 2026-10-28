"""验证记忆读取的归属/范围隔离，以及会话级覆盖合并。

使用真实内存 SQLite 和合法来源准备样本，刻意让用户 ID 与会话 ID 交叉重名。
不调用模型、不接入 /chat，不测试后续 Core/Regular 选择或 Prompt 注入。
"""

import pytest

from app import database
from app.services import memory


TIMESTAMP = "2026-10-28T10:00:00+00:00"


@pytest.fixture
def memory_reading_database():
    """准备当前会话、同用户其他会话，以及 ID 重名的其他用户和会话。"""
    connection = database.create_connection()
    try:
        database.initialize_schema(connection)
        source_ids = {}
        for conversation_id, user_id in [
            ("conversation-A", "user-001"),
            ("conversation-B", "user-001"),
            ("conversation-other", "conversation-A"),
            ("user-001", "user-other"),
        ]:
            database.upsert_conversation(
                connection, conversation_id, TIMESTAMP, user_id=user_id,
            )
            source_ids[conversation_id] = database.insert_user_message(
                connection, conversation_id, "用于读取测试的真实来源消息。", TIMESTAMP,
            )

        for scope, scope_id, key, value, source_conversation in [
            ("user", "user-001", "answer_language", "中文", "conversation-A"),
            ("conversation", "conversation-A", "answer_language", "英文", "conversation-A"),
            # 用户级信息可来自同用户的另一会话，也应跨会话读出。
            ("user", "user-001", "tech_stack", "Python + FastAPI", "conversation-B"),
            # 两条 ID 重名记录不能因为 scope_id 命中就混入当前请求。
            ("user", "conversation-A", "answer_language", "日文", "conversation-other"),
            ("conversation", "user-001", "tech_stack", "Go", "user-001"),
            # 同用户另一会话的局部记忆也不能混入。
            ("conversation", "conversation-B", "learning_goal", "其他会话目标", "conversation-B"),
        ]:
            database.upsert_memory(
                connection=connection,
                scope=scope,
                scope_id=scope_id,
                key=key,
                value=value,
                source_message_id=source_ids[source_conversation],
                updated_at=TIMESTAMP,
            )
        connection.commit()
        yield connection
    finally:
        connection.close()


def test_load_and_merge_memories_isolates_scope_and_preserves_user_defaults(
    memory_reading_database,
):
    """只读取当前两种范围；合并不依赖行顺序，也不删除用户级默认值。"""
    connection = memory_reading_database
    before = connection.execute(
        "SELECT * FROM memory ORDER BY memory_id"
    ).fetchall()

    rows = database.load_memories(
        connection,
        user_id="user-001",
        conversation_id="conversation-A",
    )

    # 资格按 scope + scope_id 筛选；保留不同 key，不只读取语言偏好。
    assert set(rows) == {
        ("user", "answer_language", "中文"),
        ("conversation", "answer_language", "英文"),
        ("user", "tech_stack", "Python + FastAPI"),
    }
    expected = {
        "answer_language": "英文",
        "tech_stack": "Python + FastAPI",
    }
    assert memory.merge_memories(rows) == expected
    assert memory.merge_memories(list(reversed(rows))) == expected

    # 覆盖只发生在返回字典中，数据库内用户级中文默认值仍然存在。
    after = connection.execute(
        "SELECT * FROM memory ORDER BY memory_id"
    ).fetchall()
    assert after == before


def test_load_memories_rejects_mismatched_conversation_owner(
    memory_reading_database,
):
    """即使提供真实存在的用户 ID，也不能读取不属于他的会话记忆。"""
    with pytest.raises(database.ConversationOwnershipError):
        database.load_memories(
            memory_reading_database,
            user_id="conversation-A",
            conversation_id="conversation-A",
        )
