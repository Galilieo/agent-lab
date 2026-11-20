"""账号与登录 session 的数据访问：注册写入、邮箱查询、session 的创建、查找和删除。

密码和 token 的哈希在 services/auth.py 完成，这里只存取哈希后的值。
"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jobpilot.db.models import User, UserSession, normalize_email


@dataclass(frozen=True)
class LoginSession:
    """一条有效的登录记录及其所属账号，供依赖函数和登出使用。"""

    session_id: UUID
    user: User


async def find_account_by_email(session: AsyncSession, email: str) -> User | None:
    """按登录标识查账号，账号状态和密码由调用方校验。"""
    return await session.scalar(
        select(User).where(func.lower(User.email) == normalize_email(email))
    )


async def create_account(
    session: AsyncSession, email: str, hashed_password: str
) -> User:
    """写入新账号并 flush；邮箱大小写变体已存在时由唯一索引抛出 IntegrityError。"""
    user = User(email=email, hashed_password=hashed_password)
    session.add(user)
    await session.flush()
    return user


async def create_login_session(
    session: AsyncSession, user_id: UUID, token_hash: str, max_age_seconds: int
) -> None:
    """登记一次登录；到期时间用数据库时钟计算，与查找时的比较保持同一时钟。"""
    session.add(
        UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=func.now() + timedelta(seconds=max_age_seconds),
        )
    )
    await session.flush()


async def find_login_session(
    session: AsyncSession, token_hash: str
) -> LoginSession | None:
    """按 token 哈希查找未过期的登录及其账号；不检查账号是否待删除。"""
    row = (
        await session.execute(
            select(UserSession.session_id, User)
            .join(User, User.user_id == UserSession.user_id)
            .where(
                UserSession.token_hash == token_hash,
                UserSession.expires_at > func.now(),
            )
        )
    ).first()
    if row is None:
        return None
    return LoginSession(session_id=row.session_id, user=row.User)


async def delete_login_session(session: AsyncSession, session_id: UUID) -> None:
    """删除一条登录记录，使对应 token 立即失效。"""
    await session.execute(
        delete(UserSession).where(UserSession.session_id == session_id)
    )
