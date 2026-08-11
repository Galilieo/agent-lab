import sqlite3

import pytest

from app.database import create_connection, initialize_schema


def test_create_connection_enables_foreign_keys() -> None:
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
