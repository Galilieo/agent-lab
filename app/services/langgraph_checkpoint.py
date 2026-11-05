"""为独立Agent图配置记录序列化与SQLite检查点连接生命周期。

由图的调用方显式提供专用文件路径；检查点表由框架管理。
不连接业务会话数据库，不调用模型；离开上下文时应关闭检查点连接。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiosqlite
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.services.llm import LLMResult, LLMToolCall


def create_checkpoint_serializer() -> JsonPlusSerializer:
    """创建内存和SQLite共用的转换配置，明确支持本图嵌套的调用记录。"""
    return JsonPlusSerializer(
        allowed_msgpack_modules=[LLMResult, LLMToolCall],
    )


@asynccontextmanager
async def open_calculator_checkpointer(
    database_path: str,
) -> AsyncIterator[AsyncSqliteSaver]:
    """提供块内可用的检查点存取组件，退出块时关闭其数据库连接。

    database_path应指向专用检查点文件，父目录由调用方准备。
    图的运行和读回应发生在上下文内；框架按需创建检查点表。
    """
    async with aiosqlite.connect(database_path) as connection:
        saver = AsyncSqliteSaver(
            connection,
            serde=create_checkpoint_serializer(),
        )
        yield saver
