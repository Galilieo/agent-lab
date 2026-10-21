"""验证两种范围记忆的 UPSERT、用户消息来源与错误写入保护。

使用真实内存 SQLite；覆盖同用户跨会话来源、范围与 key 共存，以及无效来源
不能覆盖旧值。本文件不测试 LLM 提取、记忆读取合并或上下文注入。
"""

import pytest

from app import database


FIRST_UPDATED_AT = "2026-10-19T10:00:00+00:00"
SECOND_UPDATED_AT = "2026-10-19T10:01:00+00:00"


@pytest.fixture
def memory_scenario():
    """准备两个用户、三个会话及用户/助手来源消息，供范围校验测试复用。

    每条测试独享内存连接，yield 后关闭连接；初始样本已提交。
    """
    connection = database.create_connection()
    try:
        database.initialize_schema(connection)
        for conversation_id, user_id in [
            ("conversation-A", "user-001"),
            ("conversation-B", "user-001"),
            ("conversation-other", "user-002"),
        ]:
            database.upsert_conversation(
                connection, conversation_id, FIRST_UPDATED_AT, user_id=user_id,
            )

        source_ids = {
            "source_a": database.insert_user_message(
                connection, "conversation-A",
                "请用中文回答。默认使用 Java 类比，这次直接用 Python 解释。", FIRST_UPDATED_AT,
            ),
            "source_b": database.insert_user_message(
                connection, "conversation-B",
                "以后默认先给代码，再解释。", SECOND_UPDATED_AT,
            ),
            "source_other": database.insert_user_message(
                connection, "conversation-other",
                "默认使用 Vue 类比。", FIRST_UPDATED_AT,
            ),
            "assistant_a": database.insert_assistant_message(
                connection, "conversation-A",
                "这是助手生成的猜测。", FIRST_UPDATED_AT,
            ),
        }
        connection.commit()
        yield {"connection": connection, "source_ids": source_ids}
    finally:
        connection.close()


def read_memory_rows(connection):
    """按固定顺序读取全部记忆字段，便于完整比较更新结果和失败前后的状态。"""
    return connection.execute(
        """
        SELECT scope, scope_id, key, value, source_message_id, updated_at
        FROM memory
        ORDER BY scope, scope_id, key
        """
    ).fetchall()


def test_memory_updates_only_matching_scope_owner_and_key(memory_scenario):
    """验证四条不同范围/归属/key 的记忆共存，只更新指定用户级风格及来源时间。"""
    connection = memory_scenario["connection"]
    source_ids = memory_scenario["source_ids"]
    # 建立不同范围、用户和 key 的邻居记录，防止 UPSERT 把无关记录一起覆盖。
    for scope, scope_id, key, value, source_key in [
        ("user", "user-001", "explanation_style", "使用 Java 类比", "source_a"),
        ("conversation", "conversation-A", "explanation_style", "直接用 Python 解释", "source_a"),
        ("user", "user-002", "explanation_style", "使用 Vue 类比", "source_other"),
        ("user", "user-001", "answer_language", "中文", "source_a"),
    ]:
        database.upsert_memory(
            connection=connection,
            scope=scope,
            scope_id=scope_id,
            key=key,
            value=value,
            source_message_id=source_ids[source_key],
            updated_at=FIRST_UPDATED_AT,
        )

    # 同用户另一会话的消息可以更新用户级偏好，但不应改变会话级覆盖值。
    database.upsert_memory(
        connection=connection,
        scope="user",
        scope_id="user-001",
        key="explanation_style",
        value="先给代码，再解释",
        source_message_id=source_ids["source_b"],
        updated_at=SECOND_UPDATED_AT,
    )
    rows = read_memory_rows(connection)

    # 三条风格和一条语言记忆仍为四条，只更新 user-001 的用户级风格。
    assert rows == [
        (
            "conversation", "conversation-A", "explanation_style",
            "直接用 Python 解释",
            source_ids["source_a"], FIRST_UPDATED_AT,
        ),
        (
            "user", "user-001", "answer_language",
            "中文",
            source_ids["source_a"], FIRST_UPDATED_AT,
        ),
        (
            "user", "user-001", "explanation_style",
            "先给代码，再解释",
            source_ids["source_b"], SECOND_UPDATED_AT,
        ),
        (
            "user", "user-002", "explanation_style",
            "使用 Vue 类比",
            source_ids["source_other"], FIRST_UPDATED_AT,
        ),
    ]
    # 比较完整 rows，检查作用范围、归属、key、内容、来源与更新时间。


@pytest.mark.parametrize(
    ("scope", "scope_id", "source_key"),
    [
        ("user", "user-001", "source_other"),
        ("conversation", "conversation-A", "source_b"),
        ("conversation", "conversation-A", "assistant_a"),
    ],
    ids=["different-user", "different-conversation", "assistant-source"],
)
def test_memory_rejects_invalid_source_without_overwriting(
    memory_scenario, scope, scope_id, source_key,
):
    """验证跨用户、跨会话和助手来源都被拒绝，且已有记录完全不变。"""
    connection = memory_scenario["connection"]
    source_ids = memory_scenario["source_ids"]
    database.upsert_memory(
        connection=connection,
        scope=scope,
        scope_id=scope_id,
        key="explanation_style",
        value="保留这条已确认的记忆",
        source_message_id=source_ids["source_a"],
        updated_at=FIRST_UPDATED_AT,
    )
    before = read_memory_rows(connection)

    def invalid_write():
        database.upsert_memory(
            connection=connection,
            scope=scope,
            scope_id=scope_id,
            key="explanation_style",
            value="不应写入的内容",
            source_message_id=source_ids[source_key],
            updated_at=SECOND_UPDATED_AT,
        )

    with pytest.raises(ValueError):
        invalid_write()

    # 抛出异常只说明拒绝了调用，还要确认拒绝前没有破坏已保存的值。
    after = read_memory_rows(connection)
    # 写入前后记录相同，失败不能覆盖原记忆。
    assert after == before
