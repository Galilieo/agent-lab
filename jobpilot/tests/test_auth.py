"""验证注册、登录、登出、当前用户和登录态校验。

接口测试通过 ASGITransport 在同进程调用真实应用，数据写入测试库；
纯函数测试只检查密码与 token 的哈希处理，不连接数据库。
"""

import asyncio
from datetime import timedelta
from hashlib import sha256

import httpx
import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.config import settings
from jobpilot.db.models import User, UserSession
from jobpilot.services import auth
from jobpilot.services.auth import (
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)

PASSWORD = "correct-horse-1"


async def register(
    client: httpx.AsyncClient, email: str, password: str = PASSWORD
) -> httpx.Response:
    return await client.post(
        "/api/auth/register", json={"email": email, "password": password}
    )


async def login(
    client: httpx.AsyncClient, email: str, password: str = PASSWORD
) -> httpx.Response:
    return await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )


async def sessions_of(
    session_factory: async_sessionmaker[AsyncSession], email: str
) -> list[UserSession]:
    """用新连接读回某个账号的全部登录记录。"""
    async with session_factory() as reader:
        query = (
            select(UserSession)
            .join(User, User.user_id == UserSession.user_id)
            .where(User.email == email)
        )
        return list((await reader.scalars(query)).all())


# ---------- 纯函数：密码与 token ----------


def test_password_is_hashed_with_argon2_and_verified() -> None:
    hashed = hash_password(PASSWORD)

    assert hashed.startswith("$argon2")
    assert PASSWORD not in hashed
    assert verify_password(PASSWORD, hashed)
    assert not verify_password("wrong-password", hashed)


def test_missing_account_still_spends_one_password_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """账号不存在时也做一次 argon2 验证，两种失败的耗时才接近。"""
    real_verify = auth._password_hash.verify
    checked: list[str] = []

    def spy(password: str, hashed: str) -> bool:
        checked.append(hashed)
        return real_verify(password, hashed)

    monkeypatch.setattr(auth._password_hash, "verify", spy)

    assert verify_password(PASSWORD, None) is False
    assert len(checked) == 1 and checked[0].startswith("$argon2")


def test_session_token_is_random_and_only_its_sha256_is_kept() -> None:
    first, second = new_session_token(), new_session_token()

    assert first != second
    assert len(first) >= 43  # 32 字节随机数的 URL 安全 Base64 编码
    assert hash_token(first) == sha256(first.encode()).hexdigest()
    assert len(hash_token(first)) == 64 and first not in hash_token(first)


# ---------- 注册 ----------


async def test_register_then_login_with_case_variant(
    async_client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Foo@x.com 注册后存为小写；用小写登录成功，Cookie 属性正确，库里只有哈希。"""
    created = await register(async_client, "Foo@x.com")
    assert created.status_code == 201
    assert created.json()["email"] == "foo@x.com"
    assert "password" not in created.text

    logged_in = await login(async_client, "foo@x.com")
    assert logged_in.status_code == 204

    set_cookie = logged_in.headers["set-cookie"].lower()
    assert f"{settings.cookie_name}=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert f"max-age={settings.cookie_max_age_seconds}" in set_cookie
    assert "path=/" in set_cookie

    token = async_client.cookies[settings.cookie_name]
    (stored,) = await sessions_of(session_factory, "foo@x.com")
    assert stored.token_hash == hash_token(token) != token

    me = await async_client.get("/api/me")
    assert me.status_code == 200 and me.json()["email"] == "foo@x.com"


async def test_register_rejects_duplicates_bad_input_and_client_user_id(
    async_client: httpx.AsyncClient,
) -> None:
    assert (await register(async_client, "foo@x.com")).status_code == 201
    assert (await register(async_client, "FOO@X.COM")).status_code == 409
    assert (await register(async_client, "not-an-email")).status_code == 422
    assert (await register(async_client, "a@x.com", "short")).status_code == 422

    # 身份只来自登录态：请求体里夹带 user_id 直接拒绝。
    sneaky = await async_client.post(
        "/api/auth/register",
        json={"email": "b@x.com", "password": PASSWORD, "user_id": "x"},
    )
    assert sneaky.status_code == 422


async def test_concurrent_register_creates_one_account(
    async_client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    responses = await asyncio.gather(
        register(async_client, "Race@x.com"), register(async_client, "race@x.com")
    )

    assert sorted(r.status_code for r in responses) == [201, 409]
    async with session_factory() as reader:
        count = await reader.scalar(
            select(func.count()).select_from(User).where(User.email == "race@x.com")
        )
    assert count == 1


# ---------- 登录失败 ----------


async def test_wrong_password_and_unknown_email_look_the_same(
    async_client: httpx.AsyncClient,
) -> None:
    await register(async_client, "foo@x.com")

    wrong_password = await login(async_client, "foo@x.com", "wrong-password")
    unknown_email = await login(async_client, "nobody@x.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert "set-cookie" not in wrong_password.headers
    assert "set-cookie" not in unknown_email.headers


# ---------- 登录态校验 ----------


@pytest.mark.parametrize("cookie", [None, "not-a-real-token"])
async def test_me_requires_a_valid_session(
    async_client: httpx.AsyncClient, cookie: str | None
) -> None:
    if cookie is not None:
        async_client.cookies.set(settings.cookie_name, cookie)

    assert (await async_client.get("/api/me")).status_code == 401


async def test_expired_session_is_rejected(
    async_client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await register(async_client, "foo@x.com")
    await login(async_client, "foo@x.com")
    async with session_factory.begin() as session:
        await session.execute(
            update(UserSession).values(expires_at=func.now() - timedelta(seconds=1))
        )

    assert (await async_client.get("/api/me")).status_code == 401


async def test_pending_deletion_account_can_only_log_out(
    async_client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """待删除期间仍能登录和登出，但业务接口（以 /api/me 为代表）返回 403。"""
    await register(async_client, "foo@x.com")
    async with session_factory.begin() as session:
        await session.execute(update(User).values(deletion_requested_at=func.now()))

    assert (await login(async_client, "foo@x.com")).status_code == 204
    assert (await async_client.get("/api/me")).status_code == 403
    assert (await async_client.post("/api/auth/logout")).status_code == 204


# ---------- 登出 ----------


async def test_logout_ends_only_the_current_session(
    async_client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """同一账号两处登录，登出一处后另一处仍然有效。"""
    await register(async_client, "foo@x.com")
    await login(async_client, "foo@x.com")
    first_token = async_client.cookies[settings.cookie_name]
    async_client.cookies.clear()
    await login(async_client, "foo@x.com")

    logged_out = await async_client.post("/api/auth/logout")

    assert logged_out.status_code == 204
    assert "max-age=0" in logged_out.headers["set-cookie"].lower()
    assert settings.cookie_name not in async_client.cookies
    assert (await async_client.get("/api/me")).status_code == 401
    (remaining,) = await sessions_of(session_factory, "foo@x.com")
    assert remaining.token_hash == hash_token(first_token)

    async_client.cookies.set(settings.cookie_name, first_token)
    assert (await async_client.get("/api/me")).status_code == 200
