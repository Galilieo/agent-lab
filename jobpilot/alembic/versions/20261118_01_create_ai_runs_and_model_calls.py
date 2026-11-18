"""创建业务运行与模型调用表，调用记录随运行删除匿名化。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261118_01"
down_revision: str | Sequence[str] | None = "20261116_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """先建立运行归属，再让模型调用引用同一个用户的运行。"""
    op.create_table(
        "ai_run",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), server_default="running", nullable=False),
        sa.Column("thread_id", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_ai_run")),
        sa.UniqueConstraint("run_id", "user_id", name=op.f("uq_ai_run_run_id")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.user_id"],
            name=op.f("fk_ai_run_user_id_user"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "kind IN ('parse_resume', 'parse_jd', 'match', 'tailor', 'agent')",
            name="ck_ai_run_kind",
        ),
    )
    op.create_index("ix_ai_run_user_id_started_at", "ai_run", ["user_id", "started_at"])
    op.create_table(
        "model_call",
        sa.Column("call_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("call_id", name=op.f("pk_model_call")),
        sa.ForeignKeyConstraint(
            ["run_id", "user_id"],
            ["ai_run.run_id", "ai_run.user_id"],
            name=op.f("fk_model_call_run_id_ai_run"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "(run_id IS NULL) = (user_id IS NULL)", name="ck_model_call_run_ownership"
        ),
        sa.CheckConstraint("latency_ms >= 0", name="ck_model_call_latency_ms"),
        sa.CheckConstraint("prompt_tokens >= 0", name="ck_model_call_prompt_tokens"),
        sa.CheckConstraint(
            "completion_tokens >= 0", name="ck_model_call_completion_tokens"
        ),
    )
    op.create_index("ix_model_call_run_id_user_id", "model_call", ["run_id", "user_id"])
    op.create_index(
        "ix_model_call_user_id_created_at", "model_call", ["user_id", "created_at"]
    )


def downgrade() -> None:
    """按依赖逆序移除调用记录和运行表。"""
    op.drop_table("model_call")
    op.drop_table("ai_run")
