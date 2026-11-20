"""用户隔离测试框架：用户 A 不能读、改、删用户 B 的资源，且每个接口都必须归类。

新增接口时在下面三处之一登记，否则 test_every_api_route_is_classified 失败：
- PUBLIC_ROUTES：不需要登录（注册、登录、健康检查）。
- SELF_ROUTES：只作用于调用者自己，路径里没有资源 ID（登出、当前用户）。
- OWNED_RESOURCES：属于某个用户的资源。登记创建方式、B 读取自己资源的接口，
  以及 A 会尝试的每个请求；A 的每次尝试都应返回 404，且 B 的资源保持不变。
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import httpx
import pytest

from jobpilot.main import app

Route = tuple[str, str]  # (HTTP 方法, 路径模板)

PUBLIC_ROUTES: set[Route] = {
    ("GET", "/api/health"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
}
SELF_ROUTES: set[Route] = {
    ("POST", "/api/auth/logout"),
    ("GET", "/api/me"),
}


@dataclass(frozen=True)
class Attempt:
    """A 对 B 的资源发起的一次请求。路径和请求体中的 "{id}" 会替换成 B 的资源 ID。

    请求体里放 "{id}" 用来测嵌套引用，例如 A 自己的会话引用 B 的岗位。
    """

    method: str
    path: str
    json: dict[str, Any] | None = None


@dataclass(frozen=True)
class OwnedResource:
    """一类属于用户的资源及其全部接口。"""

    name: str
    create: Callable[[httpx.AsyncClient], Awaitable[str]]  # 以 B 的身份创建，返回 ID
    read: Route  # B 读取自己这条资源的接口，用来比较前后是否被改
    attempts: tuple[Attempt, ...]
    # 该资源的全部接口（含创建、列表），用于归类检查。
    routes: frozenset[Route] = field(default_factory=frozenset)


# T1.4 起每加一类业务资源，就在这里登记一项。
OWNED_RESOURCES: list[OwnedResource] = []


def _fill(value: Any, resource_id: str) -> Any:
    """把路径或请求体中的 "{id}" 占位替换成真实资源 ID。"""
    if isinstance(value, str):
        return value.replace("{id}", resource_id)
    if isinstance(value, dict):
        return {key: _fill(item, resource_id) for key, item in value.items()}
    if isinstance(value, list):
        return [_fill(item, resource_id) for item in value]
    return value


def _api_routes() -> set[Route]:
    """从 OpenAPI 文档列出全部 /api 接口。

    FastAPI 0.163 起 include_router 不再把子路由展开到 app.routes，遍历它会漏掉
    挂载的接口，所以改用公开的 OpenAPI 文档。代价：include_in_schema=False 的接口
    不会被列出，JobPilot 不使用这个选项。
    """
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api")
        for method in operations
    }


async def _sign_in(client: httpx.AsyncClient, email: str) -> None:
    credentials = {"email": email, "password": "isolation-test-1"}
    assert (await client.post("/api/auth/register", json=credentials)).is_success
    assert (await client.post("/api/auth/login", json=credentials)).is_success


@pytest.fixture
async def user_a(async_client: httpx.AsyncClient) -> httpx.AsyncClient:
    await _sign_in(async_client, "a@isolation.invalid")
    return async_client


@pytest.fixture
async def user_b(
    async_client: httpx.AsyncClient,
) -> AsyncIterator[httpx.AsyncClient]:
    """另一个客户端，有自己的 Cookie。依赖 async_client，保证接口已指向测试库。"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        await _sign_in(client, "b@isolation.invalid")
        yield client


# ---------- 归类：新接口忘了登记时在这里失败 ----------


def test_every_api_route_is_classified() -> None:
    # 先确认能列出已知接口，防止列表为空时下面的检查空过。
    assert PUBLIC_ROUTES | SELF_ROUTES <= _api_routes()
    owned = {route for resource in OWNED_RESOURCES for route in resource.routes}
    unclassified = _api_routes() - PUBLIC_ROUTES - SELF_ROUTES - owned

    assert not unclassified, (
        f"这些接口还没登记到隔离测试：{sorted(unclassified)}，"
        "请加入 PUBLIC_ROUTES、SELF_ROUTES 或 OWNED_RESOURCES"
    )


@pytest.mark.parametrize(
    "route", sorted(_api_routes() - PUBLIC_ROUTES), ids=lambda r: f"{r[0]} {r[1]}"
)
async def test_protected_routes_require_login(
    async_client: httpx.AsyncClient, route: Route
) -> None:
    """未登录访问任何非公开接口都返回 401。"""
    method, path = route
    response = await async_client.request(method, _fill(path, str(uuid4())), json={})

    assert response.status_code == 401


# ---------- 隔离：A 访问 B 的资源 ----------


async def test_self_routes_only_show_the_caller(
    user_a: httpx.AsyncClient, user_b: httpx.AsyncClient
) -> None:
    assert (await user_a.get("/api/me")).json()["email"] == "a@isolation.invalid"
    assert (await user_b.get("/api/me")).json()["email"] == "b@isolation.invalid"


@pytest.mark.parametrize("resource", OWNED_RESOURCES, ids=lambda r: r.name)
async def test_other_users_resources_are_not_found(
    user_a: httpx.AsyncClient, user_b: httpx.AsyncClient, resource: OwnedResource
) -> None:
    """A 的每次尝试都返回 404（不是 403，不暴露资源是否存在），B 的资源不变。"""
    resource_id = await resource.create(user_b)
    read_method, read_path = resource.read
    before = await user_b.request(read_method, _fill(read_path, resource_id))
    assert before.status_code == 200

    for attempt in resource.attempts:
        response = await user_a.request(
            attempt.method,
            _fill(attempt.path, resource_id),
            json=_fill(attempt.json, resource_id),
        )
        assert response.status_code == 404, (attempt, response.text)

    after = await user_b.request(read_method, _fill(read_path, resource_id))
    assert after.json() == before.json()
