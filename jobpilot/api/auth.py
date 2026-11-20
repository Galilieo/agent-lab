"""注册、登录、登出和当前用户接口。

登录成功后把随机 token 放进 HttpOnly Cookie，数据库只保存它的 SHA-256；
之后的请求由 api/deps.py 从 Cookie 识别用户。
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from jobpilot.api.deps import CurrentUser, DbSession, current_session
from jobpilot.config import settings
from jobpilot.db.accounts import (
    LoginSession,
    create_account,
    create_login_session,
    delete_login_session,
    find_account_by_email,
)
from jobpilot.services.auth import (
    hash_password,
    hash_token,
    new_session_token,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["auth"])

_EMAIL_UNIQUE_INDEX = "uq_user_account_email_lower"


class RegisterRequest(BaseModel):
    """注册请求；多传字段（如 user_id）直接拒绝，身份只来自登录态。"""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    # 上限防止超长输入拖慢 argon2。
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """登录请求；不校验密码长度规则，规则变更后旧账号仍能登录。"""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=320)
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    """返回给前端的账号信息，不包含密码哈希。"""

    user_id: UUID
    email: str


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DbSession) -> UserOut:
    """创建账号；不自动登录，前端随后调用登录接口。"""
    try:
        user = await create_account(db, body.email, hash_password(body.password))
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        # 只把邮箱重复转成 409，其他约束错误照常抛出，避免掩盖程序缺陷。
        if error.orig.diag.constraint_name != _EMAIL_UNIQUE_INDEX:
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="该邮箱已注册"
        ) from None
    return UserOut(user_id=user.user_id, email=user.email)


@router.post("/auth/login", status_code=status.HTTP_204_NO_CONTENT)
async def login(body: LoginRequest, response: Response, db: DbSession) -> None:
    """验证邮箱和密码，登记 session 并写入 Cookie。

    邮箱不存在和密码错误返回同一错误，且都做一次密码哈希验证，
    避免通过文案或响应时间判断邮箱是否注册。待删除的账号也能登录，以便恢复。
    """
    user = await find_account_by_email(db, body.email)
    hashed = user.hashed_password if user is not None else None
    if not verify_password(body.password, hashed) or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误"
        )

    token = new_session_token()
    await create_login_session(
        db, user.user_id, hash_token(token), settings.cookie_max_age_seconds
    )
    await db.commit()
    _set_session_cookie(response, token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    login: Annotated[LoginSession, Depends(current_session)],
    db: DbSession,
) -> None:
    """删除当前这条登录记录并清除 Cookie；同一账号的其他登录不受影响。"""
    await delete_login_session(db, login.session_id)
    await db.commit()
    response.delete_cookie(
        settings.cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    """返回当前登录的账号。"""
    return UserOut(user_id=user.user_id, email=user.email)


def _set_session_cookie(response: Response, token: str) -> None:
    """把 token 原文写进 HttpOnly Cookie。"""
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.cookie_max_age_seconds,  # 与 session 的到期时间一致：7 天
        httponly=True,  # 页面上的 JS 读不到，被注入的脚本也偷不走 token
        samesite="lax",  # 从别的网站发起的 POST 请求不带这个 Cookie，防 CSRF
        secure=settings.cookie_secure,  # True 时只在 HTTPS 下发送
        path="/",
    )
