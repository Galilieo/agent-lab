"""使用真实 SQLite 验证表约束、历史窗口与提交后的持久化语义。

内存库测试数据关系，tmp_path 文件库测试重新连接后的差异；不调用模型。
多条 model_call 可以关联同一请求消息，只说明支持记录重试，不实现自动重试。
"""

import sqlite3

import pytest

from app.database import (
    create_connection,
    initialize_schema,
    load_recent_messages,
)


def test_create_connection_enables_foreign_keys() -> None:
    """检查连接工厂确实启用外键；SQLite 的该设置按连接生效。"""
    connection = create_connection()

    try:
        result = connection.execute(
            "PRAGMA foreign_keys",
        ).fetchone()

        assert result is not None
        assert result[0] == 1
    finally:
        connection.close()


def test_initialize_schema_allows_message_for_existing_conversation() -> None:
    """验证存在父会话时，消息能正常写入并按字段读回。"""
    connection = create_connection()

    try:
        initialize_schema(connection)

        connection.execute(
            """
            INSERT INTO conversation (
                conversation_id,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "active",
                "2026-08-11T10:00:00",
                "2026-08-11T10:00:00",
            ),
        )

        connection.execute(
            """
            INSERT INTO message (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "user",
                "你好",
                "2026-08-11T10:00:01",
            ),
        )

        result = connection.execute(
            """
            SELECT conversation_id, role, content
            FROM message
            """
        ).fetchone()

        assert result == (
            "conversation-001",
            "user",
            "你好",
        )
    finally:
        connection.close()


def test_initialize_schema_rejects_message_without_conversation() -> None:
    """验证孤儿消息被真实数据库外键拒绝。"""
    connection = create_connection()

    try:
        initialize_schema(connection)

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO message (
                    conversation_id,
                    role,
                    content,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    "missing-conversation",
                    "user",
                    "你好",
                    "2026-08-11T10:00:00",
                ),
            )
    finally:
        connection.close()


def test_initialize_schema_allows_retry_for_same_user_message() -> None:
    """验证一个请求消息可关联失败与成功两条调用记录，不代表自动重试已实现。"""
    connection = create_connection()

    try:
        initialize_schema(connection)

        connection.execute(
            """
            INSERT INTO conversation (
                conversation_id,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "active",
                "2026-08-12T10:00:00",
                "2026-08-12T10:00:00",
            ),
        )

        user_cursor = connection.execute(
            """
            INSERT INTO message (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "user",
                "我今年多大？",
                "2026-08-12T10:00:01",
            ),
        )
        user_message_id = user_cursor.lastrowid

        assistant_cursor = connection.execute(
            """
            INSERT INTO message (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "assistant",
                "18 岁",
                "2026-08-12T10:00:03",
            ),
        )
        assistant_message_id = assistant_cursor.lastrowid

        connection.execute(
            """
            INSERT INTO model_call (
                conversation_id,
                request_message_id,
                response_message_id,
                model,
                outcome,
                upstream_status,
                latency_ms,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "conversation-001",
                user_message_id,
                None,
                "deepseek-v4-flash",
                "timeout",
                None,
                60000.0,
                None,
                None,
                None,
                "2026-08-12T10:00:02",
            ),
        )

        connection.execute(
            """
            INSERT INTO model_call (
                conversation_id,
                request_message_id,
                response_message_id,
                model,
                outcome,
                upstream_status,
                latency_ms,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "conversation-001",
                user_message_id,
                assistant_message_id,
                "deepseek-v4-flash",
                "succeeded",
                200,
                1200.0,
                8,
                4,
                12,
                "2026-08-12T10:00:03",
            ),
        )

        results = connection.execute(
            """
            SELECT
                request_message_id,
                response_message_id,
                outcome,
                upstream_status
            FROM model_call
            ORDER BY model_call_id
            """
        ).fetchall()

        assert results == [
            (
                user_message_id,
                None,
                "timeout",
                None,
            ),
            (
                user_message_id,
                assistant_message_id,
                "succeeded",
                200,
            ),
        ]
    finally:
        connection.close()


def test_initialize_schema_rejects_invalid_model_call_references() -> None:
    """验证调用记录不能引用不存在的会话、请求消息或回复消息。"""
    connection = create_connection()

    try:
        initialize_schema(connection)

        connection.execute(
            """
            INSERT INTO conversation (
                conversation_id,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "active",
                "2026-08-12T11:00:00",
                "2026-08-12T11:00:00",
            ),
        )

        user_cursor = connection.execute(
            """
            INSERT INTO message (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "user",
                "你好",
                "2026-08-12T11:00:01",
            ),
        )
        user_message_id = user_cursor.lastrowid

        invalid_references = [
            ("missing-conversation", user_message_id, None),
            ("conversation-001", 999, None),
            ("conversation-001", user_message_id, 999),
        ]

        for (
            conversation_id,
            request_message_id,
            response_message_id,
        ) in invalid_references:
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO model_call (
                        conversation_id,
                        request_message_id,
                        response_message_id,
                        model,
                        outcome,
                        upstream_status,
                        latency_ms,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        conversation_id,
                        request_message_id,
                        response_message_id,
                        "deepseek-v4-flash",
                        "timeout",
                        None,
                        1000.0,
                        "2026-08-12T11:00:02",
                    ),
                )
    finally:
        connection.close()


def test_initialize_schema_rejects_model_call_for_message_from_other_conversation() -> None:
    """验证消息虽然存在，属于其他会话时仍会被组合外键拒绝。"""
    connection = create_connection()

    try:
        initialize_schema(connection)

        for conversation_id in (
            "conversation-a",
            "conversation-b",
        ):
            connection.execute(
                """
                INSERT INTO conversation (
                    conversation_id,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    "active",
                    "2026-08-13T10:00:00",
                    "2026-08-13T10:00:00",
                ),
            )

        user_cursor = connection.execute(
            """
            INSERT INTO message (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-b",
                "user",
                "你好",
                "2026-08-13T10:00:01",
            ),
        )
        conversation_b_message_id = user_cursor.lastrowid

        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO model_call (
                    conversation_id,
                    request_message_id,
                    response_message_id,
                    model,
                    outcome,
                    upstream_status,
                    latency_ms,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "conversation-a",
                    conversation_b_message_id,
                    None,
                    "deepseek-v4-flash",
                    "timeout",
                    None,
                    1000.0,
                    "2026-08-13T10:00:02",
                ),
            )
    finally:
        connection.close()


def test_initialize_schema_creates_message_history_index() -> None:
    """验证历史索引包含会话、创建时间和消息 ID，顺序符合现有查询设计。"""
    connection = create_connection()

    try:
        initialize_schema(connection)

        index_columns = connection.execute(
            "PRAGMA index_info('idx_message_history')"
        ).fetchall()

        assert [
            column[2]
            for column in index_columns
        ] == [
            "conversation_id",
            "created_at",
            "message_id",
        ]
    finally:
        connection.close()


def test_message_history_query_filters_conversation_and_orders_stably() -> None:
    """验证会话过滤及时间相同时的 message_id 次序，不依赖插入顺序。"""
    connection = create_connection()

    try:
        initialize_schema(connection)

        connection.executemany(
            """
            INSERT INTO conversation (
            conversation_id,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        [
            (
                "conversation-a",
                "active",
                "2026-08-14T10:00:00",
                "2026-08-14T10:00:00",
            ),
            (
                "conversation-b",
                "active",
                "2026-08-14T10:00:00",
                "2026-08-14T10:00:00",
            ),
        ],
        )

        connection.executemany(
            """
            INSERT INTO message (
            message_id,
            conversation_id,
            role,
            content,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (1, "conversation-a", "assistant", "第二条", "2026-08-14T10:00:02"),
            (2, "conversation-b", "user", "其他会话", "2026-08-14T10:00:00"),
            (3, "conversation-a", "user", "第一条", "2026-08-14T10:00:01"),
            (5, "conversation-a", "assistant", "同时消息二", "2026-08-14T10:00:03"),
            (4, "conversation-a", "user", "同时消息一", "2026-08-14T10:00:03"),
        ],
        )

        results = connection.execute(
            """
            SELECT message_id, role, content, created_at
            FROM message
            WHERE conversation_id = ?
            ORDER BY created_at, message_id
            """,
            ("conversation-a",),
        ).fetchall()

        assert results == [
            (3, "user", "第一条", "2026-08-14T10:00:01"),
            (1, "assistant", "第二条", "2026-08-14T10:00:02"),
            (4, "user", "同时消息一", "2026-08-14T10:00:03"),
            (5, "assistant", "同时消息二", "2026-08-14T10:00:03"),
        ]
    finally:
        connection.close()


def test_recent_message_window_returns_latest_messages_in_chronological_order() -> None:
    """验证先选最新 N 条，再恢复正序，且不会混入其他会话消息。"""
    connection = create_connection()

    try:
        initialize_schema(connection)

        connection.executemany(
            """
            INSERT INTO conversation (
                conversation_id,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    "conversation-a",
                    "active",
                    "2026-08-14T10:00:00",
                    "2026-08-14T10:00:00",
                ),
                (
                    "conversation-b",
                    "active",
                    "2026-08-14T10:00:00",
                    "2026-08-14T10:00:00",
                ),
            ],
        )

        connection.executemany(
            """
            INSERT INTO message (
                message_id,
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, "conversation-a", "assistant", "第二条", "2026-08-14T10:00:02"),
                (2, "conversation-b", "user", "其他会话", "2026-08-14T10:00:00"),
                (3, "conversation-a", "user", "第一条", "2026-08-14T10:00:01"),
                (5, "conversation-a", "assistant", "同时消息二", "2026-08-14T10:00:03"),
                (4, "conversation-a", "user", "同时消息一", "2026-08-14T10:00:03"),
            ],
        )

        results = load_recent_messages(
            connection,
            "conversation-a",
            2,
        )

        assert results == [
            {
                "role": "user",
                "content": "同时消息一",
            },
            {
                "role": "assistant",
                "content": "同时消息二",
            },
        ]
    finally:
        connection.close()


def test_file_database_persists_message_after_reconnecting(tmp_path) -> None:
    """验证文件库提交并关闭后，新连接仍能恢复已保存的消息。"""
    database_path = tmp_path / "agent-lab.db"

    first_connection = create_connection(str(database_path))

    try:
        initialize_schema(first_connection)

        first_connection.execute(
            """
            INSERT INTO conversation (
                conversation_id,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "active",
                "2026-08-14T11:00:00",
                "2026-08-14T11:00:00",
            ),
        )

        first_connection.execute(
            """
            INSERT INTO message (
                conversation_id,
                role,
                content,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "user",
                "重启后还能看到吗?",
                "2026-08-14T11:00:01",
            ),
        )
        first_connection.commit()
    finally:
        first_connection.close()

    second_connection = create_connection(str(database_path))

    try:
        result = second_connection.execute(
            """
            SELECT conversation_id, role, content
            FROM message
            WHERE conversation_id = ?
            """,
            ("conversation-001",),
        ).fetchone()

        assert result == (
            "conversation-001",
            "user",
            "重启后还能看到吗?",
        )
    finally:
        second_connection.close()


def test_file_database_discards_uncommitted_conversation_after_reconnecting(tmp_path,) -> None:
    """验证关闭未提交连接会丢弃该事务，后续连接无法读取这次写入。"""
    database_path = tmp_path / "uncomitted.db"

    first_connection = create_connection(str(database_path))

    try:
        initialize_schema(first_connection)

        first_connection.execute(
            """
            INSERT INTO conversation (
                conversation_id,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                "conversation-001",
                "active",
                "2026-08-14T12:00:00",
                "2026-08-14T12:00:00",
            ),
        )

        # 故意不调用 first_connection.commit()
    finally:
        first_connection.close()

    second_connection = create_connection(str(database_path))

    try:
        result = second_connection.execute(
            """
            SELECT conversation_id
            FROM conversation
            WHERE conversation_id = ?
            """,
            ("conversation-001",),
        ).fetchone()

        assert result is None
    finally:
        second_connection.close()
