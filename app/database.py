"""提供 SQLite 连接、启动建表、消息和调用记录、记忆存取。

路由通过这些函数读写数据；普通写入函数不自行提交，由调用方控制事务。
initialize_schema 用于启动阶段；模型网络等待应放在数据库事务之外。
"""

import sqlite3


class ConversationOwnershipError(Exception):
    """请求归属与已保存会话不一致；由路由转换为 HTTP 409。"""
    pass


def create_connection(
    database_path: str = ":memory:",
) -> sqlite3.Connection:
    """创建 SQLite 连接，并为这个连接启用外键检查。

    Args:
        database_path: 数据库文件路径；默认 :memory: 只存在于当前连接。

    Returns:
        由调用方负责关闭的连接。事务是否提交也由调用方决定。
    """
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(
    connection: sqlite3.Connection,
) -> None:
    """在启动阶段建表，并为旧 conversation 表补充 user_id 列。

    CREATE TABLE IF NOT EXISTS 不能修改已有表，因此必须额外检查旧库列结构。
    本函数使用 executescript，适合启动初始化，不应插入业务写入事务中。
    """
    # conversation 保存归属，message 保存对话，model_call 追踪调用，memory 保存记忆。
    # model_call 的组合外键还要求所引用消息属于同一会话，仅有消息 ID 外键不够。
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversation (
            conversation_id TEXT PRIMARY KEY NOT NULL,
            user_id TEXT,
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

        CREATE TABLE IF NOT EXISTS memory (
            memory_id INTEGER PRIMARY KEY,
            scope TEXT NOT NULL
                CHECK (scope IN ('user', 'conversation')),
            scope_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            source_message_id INTEGER NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (scope, scope_id, key),
            FOREIGN KEY (source_message_id)
                REFERENCES message (message_id)
        );
        """
    )

    # 已存在的表不会被 CREATE TABLE 改写；通过列探测兼容未带 user_id 的旧库。
    columns = connection.execute(
        "PRAGMA table_info(conversation)"
    ).fetchall()
    column_names = {column[1] for column in columns}

    if "user_id" not in column_names:
        connection.execute(
            "ALTER TABLE conversation ADD COLUMN user_id TEXT"
        )


def upsert_conversation(
    connection: sqlite3.Connection,
    conversation_id: str,
    timestamp: str,
    user_id: str | None = None,
) -> None:
    """创建会话，或仅在归属相同时更新其活跃时间。

    匿名归属用 NULL 表示，已有会话不自动认领或更换用户，created_at 保持不变。

    Raises:
        ConversationOwnershipError: 冲突行归属不匹配，条件更新没有写入记录。
    """
    # IS 让双方为 NULL 的匿名归属也能匹配；普通等号不能用来判断两个 NULL 相等。
    cursor = connection.execute(
        """
        INSERT INTO conversation (
            conversation_id,
            user_id,
            status,
            created_at,
            updated_at
        )
        VALUES (?, ?, 'active', ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            updated_at = excluded.updated_at
        WHERE conversation.user_id IS excluded.user_id
        """,
        (
            conversation_id,
            user_id,
            timestamp,
            timestamp,
        ),
    )

    if cursor.rowcount == 0:
        raise ConversationOwnershipError(
            "Conversation ownership does not match."
        )


def upsert_memory(
    connection: sqlite3.Connection,
    scope: str,
    scope_id: str,
    key: str,
    value: str,
    source_message_id: int,
    updated_at: str,
) -> None:
    """校验用户消息来源后，按范围、归属和 key 新增或更新记忆。

    用户级来源可以来自同用户的不同会话；会话级来源必须来自指定会话。
    冲突时只更新内容、来源和时间，提交事务由调用方负责。

    Args:
        connection: 已初始化的 SQLite 连接。
        scope: user 或 conversation，决定 scope_id 的含义。
        scope_id: 应用绑定的用户或会话标识。
        key: 要新增或更新的记忆类别。
        value: 本次确认的记忆内容。
        source_message_id: 真实用户消息的 ID，不接受助手消息作为来源。
        updated_at: 由调用方提供的更新时间。

    Raises:
        ValueError: 来源不存在、不是用户消息，或与目标范围及归属不匹配。
    """
    # SELECT 先筛选来源，再进入 INSERT/UPSERT；错误来源不会覆盖已保存的记忆。
    cursor = connection.execute(
        """
        INSERT INTO memory (
            scope,
            scope_id,
            key,
            value,
            source_message_id,
            updated_at
        )
        SELECT
            :scope,
            :scope_id,
            :key,
            :value,
            :source_message_id,
            :updated_at
        FROM message AS m
        JOIN conversation AS c
            ON c.conversation_id = m.conversation_id
        WHERE m.message_id = :source_message_id
            AND m.role = 'user'
            AND (
                (:scope = 'user' AND c.user_id = :scope_id)
                OR
                (
                    :scope = 'conversation'
                    AND m.conversation_id = :scope_id
                )
            )
        ON CONFLICT(scope, scope_id, key) DO UPDATE SET
            value = excluded.value,
            source_message_id = excluded.source_message_id,
            updated_at = excluded.updated_at
        """,
        {
            "scope": scope,
            "scope_id": scope_id,
            "key": key,
            "value": value,
            "source_message_id": source_message_id,
            "updated_at": updated_at,
        },
    )

    # 零行 SELECT 在 SQL 层是合法操作，需主动转换成调用方可感知的拒绝。
    if cursor.rowcount == 0:
        raise ValueError(
            "Source message does not match memory scope."
        )


def validate_conversation_owner(
    connection: sqlite3.Connection,
    *,
    user_id: str | None,
    conversation_id: str,
) -> None:
    """核对已有会话的归属，供读取和管理共用，不修改数据。"""
    conversation = connection.execute(
        "SELECT user_id FROM conversation WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchone()

    if conversation is None:
        raise ValueError("Conversation does not exist.")

    if conversation[0] != user_id:
        raise ConversationOwnershipError(
            "Conversation ownership does not match."
        )


def load_memories(
    connection: sqlite3.Connection,
    *,
    user_id: str | None,
    conversation_id: str,
) -> list[tuple[str, str, str]]:
    """核对归属后读取 (scope, key, value)，连接由调用方管理。"""
    validate_conversation_owner(
        connection, user_id=user_id, conversation_id=conversation_id,
    )
    return connection.execute(
        """
        SELECT scope, key, value
        FROM memory
        WHERE (scope = 'user' AND scope_id = :user_id)
            OR (scope = 'conversation' AND scope_id = :conversation_id)
        """,
        {
            "user_id": user_id,
            "conversation_id": conversation_id,
        },
    ).fetchall()


def list_memory_records(
    connection: sqlite3.Connection,
    *,
    user_id: str | None,
    conversation_id: str,
) -> list[dict]:
    """查看当前可见的原始记忆和来源，不合并、不提交事务。"""
    validate_conversation_owner(
        connection, user_id=user_id, conversation_id=conversation_id,
    )
    rows = connection.execute(
        """
        SELECT scope, scope_id, key, value, source_message_id, updated_at
        FROM memory
        WHERE (scope = 'user' AND scope_id = :user_id)
            OR (scope = 'conversation' AND scope_id = :conversation_id)
        ORDER BY scope, key
        """,
        {"user_id": user_id, "conversation_id": conversation_id},
    ).fetchall()
    fields = ("scope", "scope_id", "key", "value", "source_message_id", "updated_at")
    return [dict(zip(fields, row)) for row in rows]


def delete_memory_records(
    connection: sqlite3.Connection,
    *,
    user_id: str | None,
    conversation_id: str,
    key: str,
    target: str,
) -> int:
    """按明确目标删除某个 key；不自行提交，返回删除条数。"""
    validate_conversation_owner(
        connection,
        user_id=user_id,
        conversation_id=conversation_id,
    )

    if target not in ("user", "conversation", "all"):
        raise ValueError("Invalid memory deletion target.")

    if target in ("user", "all") and user_id is None:
        raise ValueError("User-scoped deletion requires user_id.")

    if target in ("user", "conversation"):
        scope_id = user_id if target == "user" else conversation_id

        cursor = connection.execute(
            """
            DELETE FROM memory
            WHERE scope = :scope
              AND scope_id = :scope_id
              AND key = :key
            """,
            {
                "scope": target,
                "scope_id": scope_id,
                "key": key,
            },
        )
    else:
        cursor = connection.execute(
            """
            DELETE FROM memory
            WHERE key = :key
              AND (
                  (scope = 'user' AND scope_id = :user_id)
                  OR
                  (
                      scope = 'conversation'
                      AND scope_id IN (
                          SELECT conversation_id
                          FROM conversation
                          WHERE user_id = :user_id
                      )
                  )
              )
            """,
            {
                "key": key,
                "user_id": user_id,
            },
        )

    return cursor.rowcount


def insert_user_message(
    connection: sqlite3.Connection,
    conversation_id: str,
    content: str,
    created_at: str,
) -> int:
    """保存当前用户消息并返回生成的 message_id，供调用记录关联。

    不自行提交；路由需先完成旧历史读取，再写入当前消息，防止上下文重复。
    """
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
    """保存成功生成的最终回答，返回用于关联最终调用的 message_id。

    与成功 model_call 一起提交，模型失败时不调用本函数。
    """
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


def update_assistant_message_content(
    connection: sqlite3.Connection,
    conversation_id: str,
    message_id: int,
    content: str,
) -> None:
    """更新指定会话中的原助手消息，事务由调用方管理。"""
    cursor = connection.execute(
        """
        UPDATE message
        SET content = ?
        WHERE conversation_id = ?
        AND message_id = ?
        AND role = 'assistant'
        """,
        (content, conversation_id, message_id),
    )

    if cursor.rowcount != 1:
        raise ValueError("Assistant message does not match conversation.")


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
    """保存一次成功的模型调用元数据，不提交事务。

    中间工具请求尚无最终回答，response_message_id 可以为 None；
    只有生成最终回答的调用才关联最终 assistant message。
    """
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
    """保存失败调用的分类、状态和耗时，不伪造回答或 Token 数据。

    request_message_id 仍关联本轮已保存的用户消息，由调用方提交。
    """
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
    """读取指定会话最近 limit 条消息，并恢复为模型需要的时间正序。

    内层倒序选最新 N 条，外层再正序；时间相同时用 message_id 保证稳定顺序。
    返回 role/content 字典列表，不包含其他会话消息，也不读取长期记忆。
    """
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
