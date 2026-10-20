import pytest

from app import database


FIRST_UPDATED_AT = "2026-10-19T10:00:00+00:00"
SECOND_UPDATED_AT = "2026-10-19T10:01:00+00:00"


@pytest.fixture
def memory_scenario():
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
    return connection.execute(
        """
        SELECT scope, scope_id, key, value, source_message_id, updated_at
        FROM memory
        ORDER BY scope, scope_id, key
        """
    ).fetchall()


def test_memory_updates_only_matching_scope_owner_and_key(memory_scenario):
    connection = memory_scenario["connection"]
    source_ids = memory_scenario["source_ids"]
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

    after = read_memory_rows(connection)
    # 写入前后记录相同，失败不能覆盖原记忆。
    assert after == before
