"""在测试库的一次可回滚事务里验证旧账号升级、冲突保护与对称回退。"""

from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import command


async def test_account_revision_round_trip(db_engine: AsyncEngine) -> None:
    """旧库碰撞时保留原状，解决后可升级，回退可恢复原有表名和约束。"""
    async with db_engine.connect() as connection:
        await connection.run_sync(check_account_revision)
        # 包含迁移、合成账号和 Alembic 版本行的改动一起回滚。
        await connection.rollback()


def check_account_revision(connection: Connection) -> None:
    """以同一连接重放迁移，用 savepoint 隔离预期的冲突错误。"""
    connection.begin()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["connection"] = connection
    previous, revision = "20261118_01", "20261118_02"
    command.downgrade(config, previous)
    original = inspect(connection)
    original_fks = {
        name: original.get_foreign_keys(name) for name in ("user_session", "ai_run")
    }
    insert_account = text(
        """INSERT INTO "user" (user_id, email, hashed_password)
           VALUES (:id, :email, 'test')"""
    )
    user_id, other_id = uuid4(), uuid4()
    connection.execute(
        insert_account,
        [
            {"id": user_id, "email": "Foo@example.invalid"},
            {"id": other_id, "email": "foo@example.invalid"},
        ],
    )
    with pytest.raises(DBAPIError, match=r"duplicate lower\(email\)"):
        with connection.begin_nested():
            command.upgrade(config, revision)
    assert (
        connection.scalar(text("SELECT version_num FROM alembic_version")) == previous
    )
    assert connection.scalar(text('SELECT count(*) FROM "user"')) == 2

    connection.execute(text('DELETE FROM "user" WHERE user_id=:id'), {"id": other_id})
    command.upgrade(config, revision)
    upgraded = inspect(connection)
    assert upgraded.has_table("user_account") and not upgraded.has_table("user")
    assert upgraded.get_pk_constraint("user_account")["name"] == "pk_user_account"
    assert (
        connection.scalar(text("SELECT email FROM user_account"))
        == "foo@example.invalid"
    )
    assert "is_active" not in {
        col["name"] for col in upgraded.get_columns("user_account")
    }
    for name in original_fks:
        (fk,) = upgraded.get_foreign_keys(name)
        assert fk["referred_table"] == "user_account"
        assert fk["name"] == f"fk_{name}_user_id_user_account"

    command.downgrade(config, previous)
    restored = inspect(connection)
    assert restored.has_table("user") and not restored.has_table("user_account")
    assert restored.get_pk_constraint("user")["name"] == "pk_user"
    assert restored.get_unique_constraints("user")[0]["name"] == "uq_user_email"
    for name, fks in original_fks.items():
        assert restored.get_foreign_keys(name) == fks
    assert connection.scalar(text('SELECT is_active FROM "user"')) is True
    assert not next(
        col for col in restored.get_columns("model_call") if col["name"] == "latency_ms"
    )["nullable"]
