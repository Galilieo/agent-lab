"""通过同进程 HTTP 请求验证健康接口；SQLAlchemy 与测试 PostgreSQL 真实执行。"""

import httpx


async def test_health_checks_real_test_database(
    async_client: httpx.AsyncClient,
) -> None:
    """应用使用测试库 session 完成 SELECT 1 后，返回健康状态。"""
    response = await async_client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
