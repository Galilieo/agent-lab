"""从 Cookie 识别当前请求的用户；业务接口只从这里取得 user_id。"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from jobpilot.config import settings
from jobpilot.db.accounts import LoginSession, find_login_session
from jobpilot.db.models import User
from jobpilot.db.session import get_session
from jobpilot.services.auth import hash_token

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def current_session(request: Request, db: DbSession) -> LoginSession:
    """登录有效即通过，不看账号状态；登出和以后的恢复账号使用。"""
    token = request.cookies.get(settings.cookie_name)
    login = await find_login_session(db, hash_token(token)) if token else None
    if login is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或登录已过期"
        )
    return login


async def current_user(
    login: Annotated[LoginSession, Depends(current_session)],
) -> User:
    """在登录有效的基础上拒绝待删除账号；业务接口都用它取得当前用户。"""
    if login.user.deletion_requested_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="账号待删除，只能恢复或登出"
        )
    return login.user


CurrentUser = Annotated[User, Depends(current_user)]
