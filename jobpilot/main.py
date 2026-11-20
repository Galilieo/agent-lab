"""提供 JobPilot HTTP 入口，管理数据库生命周期并检查连通性。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.api.auth import router as auth_router
from jobpilot.config import settings
from jobpilot.db.session import check_database, create_database_engine, get_session


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """启动时准备连接池与 session 工厂，退出时释放连接池。"""
    engine = create_database_engine(
        settings.database_url,
        connect_timeout_seconds=settings.database_connect_timeout_seconds,
    )
    app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="JobPilot", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/api/health")
async def health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    """通过请求专属的 session 执行查询，检查 PostgreSQL 连通性。"""
    try:
        await check_database(session)
    except SQLAlchemyError:
        # 不把连接信息、驱动异常或数据库内部细节返回给浏览器。
        raise HTTPException(status_code=503, detail="数据库暂不可用") from None
    return {"status": "ok", "database": "ok"}
