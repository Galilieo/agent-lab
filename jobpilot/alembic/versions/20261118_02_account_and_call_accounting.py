"""改名账号表并规范邮箱，支持发送前记账和运行终态校验。"""

import sqlalchemy as sa

from alembic import op

revision = "20261118_02"
down_revision = "20261118_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """先锁定账号并检查邮箱碰撞，冲突时整条迁移回滚。"""
    op.execute('LOCK TABLE "user" IN ACCESS EXCLUSIVE MODE')
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT lower(email) FROM "user"
                GROUP BY lower(email) HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Resolve duplicate lower(email) before upgrading';
            END IF;
        END $$
    """)
    op.rename_table("user", "user_account")
    op.execute("ALTER TABLE user_account RENAME CONSTRAINT pk_user TO pk_user_account")
    op.execute(
        "ALTER TABLE user_session RENAME CONSTRAINT fk_user_session_user_id_user "
        "TO fk_user_session_user_id_user_account"
    )
    op.execute(
        "ALTER TABLE ai_run RENAME CONSTRAINT fk_ai_run_user_id_user "
        "TO fk_ai_run_user_id_user_account"
    )
    op.drop_constraint("uq_user_email", "user_account", type_="unique")
    op.execute(
        "UPDATE user_account SET email = lower(email) WHERE email <> lower(email)"
    )
    op.create_index(
        "uq_user_account_email_lower",
        "user_account",
        [sa.text("lower(email)")],
        unique=True,
    )
    op.drop_column("user_account", "is_active")

    op.alter_column("model_call", "latency_ms", nullable=True)
    op.create_check_constraint(
        "ck_model_call_unknown_usage",
        "model_call",
        "outcome <> 'unknown' OR (prompt_tokens IS NULL AND completion_tokens IS NULL)",
    )
    op.create_check_constraint(
        "ck_ai_run_status",
        "ai_run",
        "status IN ('running', 'waiting_confirmation', 'succeeded', "
        "'failed', 'cancelled', 'budget_exhausted')",
    )
    op.create_check_constraint(
        "ck_ai_run_finished_at",
        "ai_run",
        "(status IN ('running', 'waiting_confirmation')) = (finished_at IS NULL)",
    )


def downgrade() -> None:
    """恢复旧结构；若已有耗时未知的调用，旧列的 NOT NULL 会阻止回退。"""
    op.alter_column("model_call", "latency_ms", nullable=False)
    op.drop_constraint("ck_model_call_unknown_usage", "model_call", type_="check")
    op.drop_constraint("ck_ai_run_finished_at", "ai_run", type_="check")
    op.drop_constraint("ck_ai_run_status", "ai_run", type_="check")

    op.add_column(
        "user_account",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.drop_index("uq_user_account_email_lower", table_name="user_account")
    op.create_unique_constraint("uq_user_email", "user_account", ["email"])
    op.execute(
        "ALTER TABLE ai_run RENAME CONSTRAINT fk_ai_run_user_id_user_account "
        "TO fk_ai_run_user_id_user"
    )
    op.execute(
        "ALTER TABLE user_session RENAME CONSTRAINT "
        "fk_user_session_user_id_user_account TO fk_user_session_user_id_user"
    )
    op.execute("ALTER TABLE user_account RENAME CONSTRAINT pk_user_account TO pk_user")
    op.rename_table("user_account", "user")
