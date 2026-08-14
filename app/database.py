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
