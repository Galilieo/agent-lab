"""提供注册写入与登录、恢复账号共用的邮箱查询规则。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jobpilot.db.models import User, normalize_email


async def find_account_by_email(session: AsyncSession, email: str) -> User | None:
    """按登录标识查账号，账号状态和密码由调用方校验。"""
    return await session.scalar(
        select(User).where(func.lower(User.email) == normalize_email(email))
    )
