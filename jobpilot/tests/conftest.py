"""准备真实测试库、同进程 HTTP 客户端及假模型，不连接开发库或模型服务。

数据库与接口测试使用按测试创建的引擎，业务数据在测试前后清空。
ASGITransport 不触发应用启动，此处替换 session 依赖，避免创建开发库连接池。
"""

from argparse import Namespace
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from alembic.config import Config
from sqlalchemy import URL, delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from alembic import command
from jobpilot.config import settings
from jobpilot.db.models import Base
from jobpilot.db.session import create_database_engine, get_session
from jobpilot.main import app
from jobpilot.tests.fakes import FakeModelClient


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """阻止默认 HTTP 传输访问外网；ASGITransport 仍可调用本地应用。"""

    def reject_sync(
        transport: httpx.HTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        raise AssertionError("测试禁止外部 HTTP 请求，请使用假模型客户端")

    async def reject_async(
        transport: httpx.AsyncHTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        raise AssertionError("测试禁止外部 HTTP 请求，请使用假模型客户端")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", reject_sync)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject_async)


@pytest.fixture(scope="session")
def migrated_test_database() -> URL:
    """先检查数据库身份，再把独立测试库迁移到最新版本。"""
    database_url = settings.test_database_url
    if (
        database_url.host not in {"127.0.0.1", "localhost"}
        or database_url.database != "jobpilot_test"
        or database_url.database == settings.database_url.database
    ):
        raise RuntimeError("测试只允许使用与开发库分开的本机 jobpilot_test")

    migration_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    migration_config.cmd_opts = Namespace(x=["database=test"])
    command.upgrade(migration_config, "head")
    return database_url


async def clear_business_tables(engine: AsyncEngine) -> None:
    """按外键依赖逆序清空模型中的业务表，保留 Alembic 版本信息。"""
    async with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            await connection.execute(delete(table))


@pytest.fixture
async def db_engine(migrated_test_database: URL) -> AsyncIterator[AsyncEngine]:
    """为每个测试创建引擎，并保证测试数据清理和连接池释放。"""
    engine = create_database_engine(
        migrated_test_database,
        connect_timeout_seconds=settings.database_connect_timeout_seconds,
    )
    try:
        await clear_business_tables(engine)
        try:
            yield engine
        finally:
            await clear_business_tables(engine)
    finally:
        await engine.dispose()


@pytest.fixture
def session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """提供可新建多个 session 的工厂，方便验证提交后重新读取。"""
    return async_sessionmaker(db_engine, expire_on_commit=False)


@pytest.fixture
async def db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """提供本次测试的数据库 session，用完关闭，提交仍由测试明确执行。"""
    async with session_factory() as session:
        yield session


@pytest.fixture
async def async_client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[httpx.AsyncClient]:
    """把真实应用的数据库依赖切换到测试库，用完恢复原有依赖配置。"""

    async def get_test_session() -> AsyncIterator[AsyncSession]:
        """为每个接口请求独立创建测试库 session。"""
        async with session_factory() as session:
            yield session

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_session] = get_test_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def fake_model_client() -> FakeModelClient:
    """为每个测试新建客户端，避免预设响应和调用记录互相污染。"""
    return FakeModelClient()
