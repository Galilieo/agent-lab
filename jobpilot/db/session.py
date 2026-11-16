"""创建异步数据库引擎，并为 HTTP 请求提供独立的 ORM session。"""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_database_engine(
    database_url: URL, *, connect_timeout_seconds: int
) -> AsyncEngine:
    """创建连接池；实际数据库连接在执行查询时获取。"""
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": connect_timeout_seconds},
    )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """为本次请求创建并关闭 session，事务提交由业务层负责。

    关闭时会回滚尚未提交的事务；不能把请求正常返回视为自动提交。
    """
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.db_session_factory
    )
    async with session_factory() as session:
        yield session


async def check_database(session: AsyncSession) -> None:
    """执行轻量查询，连接或查询失败时让数据库异常交给调用方处理。"""
    await session.execute(text("SELECT 1"))
