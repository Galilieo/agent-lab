"""提供 JobPilot HTTP 入口和真实查询数据库的健康检查。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from jobpilot.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用启动时创建连接池，退出时释放；实际连接在请求时获取。"""
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    app.state.db_engine = engine
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title="JobPilot", lifespan=lifespan)


@app.get("/api/health")
async def health(request: Request) -> dict[str, str]:
    """执行一次数据库查询，确认当前服务能够访问 PostgreSQL。"""
    try:
        async with request.app.state.db_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # 不把连接信息、驱动异常或数据库内部细节返回给浏览器。
        raise HTTPException(
            status_code=503, detail="数据库暂不可用"
        ) from None
    return {"status": "ok", "database": "ok"}
