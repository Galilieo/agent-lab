import sqlite3


def create_connection(
    database_path: str = ":memory:",
) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversation (
            conversation_id TEXT PRIMARY KEY NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS message (
            message_id INTEGER PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (conversation_id, message_id),
            FOREIGN KEY (conversation_id)
                REFERENCES conversation (conversation_id)
        );

        CREATE INDEX IF NOT EXISTS idx_message_history
        ON message (conversation_id, created_at, message_id);

        CREATE TABLE IF NOT EXISTS model_call (
            model_call_id INTEGER PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            request_message_id INTEGER NOT NULL,
            response_message_id INTEGER,
            model TEXT NOT NULL,
            outcome TEXT NOT NULL,
            upstream_status INTEGER,
            latency_ms REAL NOT NULL,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id)
                REFERENCES conversation (conversation_id),
            FOREIGN KEY (conversation_id, request_message_id)
                REFERENCES message (conversation_id, message_id),
            FOREIGN KEY (conversation_id, response_message_id)
                REFERENCES message (conversation_id, message_id)
        );
        """
    )


def upsert_conversation(
    connection: sqlite3.Connection,
    conversation_id: str,
    timestamp: str,
) -> None:
    connection.execute(
        """
        INSERT INTO conversation (
            conversation_id,
            status,
            created_at,
            updated_at
        )
        VALUES (?, 'active', ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            updated_at = excluded.updated_at
        """,
        (
            conversation_id,
            timestamp,
            timestamp,
        ),
    )


def insert_user_message(
    connection: sqlite3.Connection,
    conversation_id: str,
    content: str,
    created_at: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO message (
            conversation_id,
            role,
            content,
            created_at
        )
        VALUES (?, 'user', ?, ?)
        """,
        (
            conversation_id,
            content,
            created_at,
        ),
    )

    return cursor.lastrowid


def insert_assistant_message(
    connection: sqlite3.Connection,
    conversation_id: str,
    content: str,
    created_at: str,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO message (
            conversation_id,
            role,
            content,
            created_at
        )
        VALUES (?, 'assistant', ?, ?)
        """,
        (
            conversation_id,
            content,
            created_at,
        ),
    )

    return cursor.lastrowid


def insert_successful_model_call(
    connection: sqlite3.Connection,
    conversation_id: str,
    request_message_id: int,
    response_message_id: int | None,
    model: str,
    upstream_status: int,
    latency_ms: float,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    created_at: str,
) -> None:
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
        VALUES (?, ?, ?, ?, 'succeeded', ?, ?, ?, ?, ?, ?)
        """,
        (
            conversation_id,
            request_message_id,
            response_message_id,
            model,
            upstream_status,
            latency_ms,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            created_at,
        ),
    )


def insert_failed_model_call(
    connection: sqlite3.Connection,
    conversation_id: str,
    request_message_id: int,
    model: str,
    outcome: str,
    upstream_status: int | None,
    latency_ms: float,
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO model_call (
            conversation_id,
            request_message_id,
            model,
            outcome,
            upstream_status,
            latency_ms,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            conversation_id,
            request_message_id,
            model,
            outcome,
            upstream_status,
            latency_ms,
            created_at,
        ),
    )


def load_recent_messages(
    connection: sqlite3.Connection,
    conversation_id: str,
    limit: int,
) -> list[dict[str, str]]:
    rows = connection.execute(
        """
        SELECT role, content
        FROM (
            SELECT role, content, created_at, message_id
            FROM message
            WHERE conversation_id = ?
            ORDER BY created_at DESC, message_id DESC
            LIMIT ?
        )
        ORDER BY created_at, message_id
        """,
        (conversation_id, limit),
    ).fetchall()

    return [
        {
            "role": role,
            "content": content,
        }
        for role, content in rows
    ]
