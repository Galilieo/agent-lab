"""验证用户在测试库中提交后可由新 session 读出，并保护逐测试的数据清理。"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.db.models import User


@pytest.mark.parametrize(
    "email",
    ["fixture-check@example.invalid", "fixture-check@example.invalid"],
    ids=["first-test", "next-test"],
)
async def test_committed_user_is_readable_in_new_session(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    email: str,
) -> None:
    """两个测试实例复用相同邮箱，均应从空库开始并能独立提交。"""
    assert await db_session.scalar(select(func.current_database())) == "jobpilot_test"
    assert await db_session.scalar(select(func.count()).select_from(User)) == 0
    user = User(email=email, hashed_password="synthetic-hash-for-persistence-only")
    db_session.add(user)

    await db_session.commit()

    async with session_factory() as reading_session:
        saved_user = await reading_session.get(User, user.user_id)
        assert saved_user is not None
        assert saved_user.email == email
