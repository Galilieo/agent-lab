"""用真实 PostgreSQL 验证邮箱身份、运行归属及终态约束。"""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.db.accounts import find_account_by_email
from jobpilot.db.models import AiRun, RunStatus, User
from jobpilot.db.runs import set_run_status


async def test_account_email_identity(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """并发写大小写变体只创建一个账号，后续查找兼容原输入。"""

    async def register(email: str) -> bool:
        try:
            async with session_factory.begin() as session:
                session.add(User(email=email, hashed_password="test-hash"))
        except IntegrityError as exc:
            assert exc.orig.diag.constraint_name == "uq_user_account_email_lower"
            return False
        return True

    assert sorted(
        await asyncio.gather(register("Foo@x.com"), register("foo@x.com"))
    ) == [False, True]
    async with session_factory() as session:
        account = await find_account_by_email(session, "FoO@x.COM")
        assert account is not None and account.email == "foo@x.com"
        assert account is await find_account_by_email(session, "foo@x.com")
        with pytest.raises(IntegrityError) as error:
            await session.execute(
                insert(User.__table__).values(email="FOO@x.com", hashed_password="test")
            )
        assert error.value.orig.diag.constraint_name == "uq_user_account_email_lower"


@pytest.mark.parametrize(
    "terminal",
    [
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
        RunStatus.BUDGET_EXHAUSTED,
    ],
)
async def test_run_terminal_time(
    db_session: AsyncSession,
    terminal: RunStatus,
) -> None:
    """等待可继续，终态附结束时间，其他用户及迟到的更新不能改写它。"""
    user = User(email="run@example.invalid", hashed_password="test")
    db_session.add(user)
    await db_session.flush()
    run = AiRun(user_id=user.user_id, kind="agent")
    db_session.add(run)
    await db_session.flush()
    assert not await set_run_status(db_session, uuid4(), run.run_id, terminal)
    assert await set_run_status(
        db_session, user.user_id, run.run_id, RunStatus.WAITING_CONFIRMATION
    )
    await db_session.refresh(run)
    assert run.status == RunStatus.WAITING_CONFIRMATION and run.finished_at is None
    assert await set_run_status(db_session, user.user_id, run.run_id, RunStatus.RUNNING)
    assert await set_run_status(db_session, user.user_id, run.run_id, terminal)
    assert not await set_run_status(
        db_session, user.user_id, run.run_id, RunStatus.RUNNING
    )
    await db_session.commit()
    await db_session.refresh(run)
    assert run.status == terminal and run.finished_at is not None


@pytest.mark.parametrize(
    ("status", "finished", "constraint"),
    [
        ("invalid", True, "ck_ai_run_status"),
        ("failed", False, "ck_ai_run_finished_at"),
        ("running", True, "ck_ai_run_finished_at"),
    ],
)
async def test_run_status_checks(
    db_session: AsyncSession,
    status: str,
    finished: bool,
    constraint: str,
) -> None:
    """绕过状态更新函数，非法状态与结束时间组合仍被数据库拒绝。"""
    user = User(email="state@example.invalid", hashed_password="test")
    db_session.add(user)
    await db_session.flush()
    db_session.add(AiRun(user_id=user.user_id, kind="tailor"))
    await db_session.flush()
    with pytest.raises(IntegrityError) as error:
        await db_session.execute(
            update(AiRun).values(
                status=status,
                finished_at=func.now() if finished else None,
            )
        )
    assert error.value.orig.diag.constraint_name == constraint
