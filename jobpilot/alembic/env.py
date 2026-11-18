"""连接配置指定的 PostgreSQL，并用模型元数据执行或生成迁移。"""

import asyncio
from logging.config import fileConfig

from jobpilot.config import settings

# 导入模型模块，使自动生成能看到完整的表结构。
from jobpilot.db.models import Base
from sqlalchemy import URL, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def get_database_url() -> URL:
    """默认迁移开发库；显式 -x database=test 时使用独立测试库。"""
    database = context.get_x_argument(as_dictionary=True).get("database", "development")
    if database == "test":
        return settings.test_database_url
    if database == "development":
        return settings.database_url
    raise ValueError("database 只能是 development 或 test")


def run_migrations_offline() -> None:
    """输出迁移 SQL，供检查使用；不连接数据库。"""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """在现有连接上配置 Alembic，并用事务执行迁移。"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """为本次迁移创建独立连接，结束后释放；不复用 HTTP 连接池。"""
    engine = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """使用调用方提供的连接，或为 CLI 新建异步迁移连接。"""
    connection = config.attributes.get("connection")
    if connection is not None:
        do_run_migrations(connection)
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
