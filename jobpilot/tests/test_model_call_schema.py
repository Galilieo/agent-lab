"""通过真实测试库验证模型调用与运行的归属约束。"""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobpilot.db.models import AiRun, ModelCall, User


async def test_model_call_cannot_reference_another_users_run(
    db_session: AsyncSession,
) -> None:
    """即使用户和运行分别都存在，数据库也拒绝跨用户关联。"""
    owner = User(email="run-owner@example.invalid", hashed_password="synthetic")
    other_user = User(email="other-user@example.invalid", hashed_password="synthetic")
    db_session.add_all([owner, other_user])
    await db_session.flush()
    run_id = uuid4()
    await db_session.execute(
        text(
            "INSERT INTO ai_run (run_id, user_id, kind) "
            "VALUES (:run, :owner, 'parse_jd')"
        ),
        {"run": run_id, "owner": owner.user_id},
    )

    with pytest.raises(IntegrityError) as error:
        await db_session.execute(
            text(
                """
                INSERT INTO model_call
                    (call_id, run_id, user_id, purpose, model, outcome, latency_ms)
                VALUES (:call, :run, :owner, 'parse_jd', 'test-model', 'success', 10)
                """
            ),
            {"call": uuid4(), "run": run_id, "owner": other_user.user_id},
        )

    assert getattr(error.value.orig, "sqlstate", None) == "23503"


async def test_deleted_user_leaves_anonymous_call_statistics(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """账号与运行删除后，另一会话仍可读取去掉归属的调用用量。"""
    owner = User(email="deleted-owner@example.invalid", hashed_password="synthetic")
    db_session.add(owner)
    await db_session.flush()
    run = AiRun(user_id=owner.user_id, kind="parse_jd")
    db_session.add(run)
    await db_session.flush()
    model_call = ModelCall(
        user_id=owner.user_id,
        run_id=run.run_id,
        purpose="parse_jd",
        model="test-model",
        outcome="invalid_output",
        latency_ms=10,
        prompt_tokens=42,
    )
    db_session.add(model_call)
    await db_session.commit()

    await db_session.delete(owner)
    await db_session.commit()

    async with session_factory() as reading_session:
        assert await reading_session.get(AiRun, run.run_id) is None
        saved_call = await reading_session.get(ModelCall, model_call.call_id)
        assert saved_call is not None
        assert saved_call.user_id is None
        assert saved_call.run_id is None
        assert saved_call.outcome == "invalid_output"
        assert saved_call.prompt_tokens == 42
        assert saved_call.completion_tokens is None
