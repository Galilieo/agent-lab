"""启用 vector 扩展并创建用户、登录记录，回退时按外键依赖逆序删表。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261116_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """启用扩展，先建用户表，再建带用户外键的登录记录表。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "user",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_user")),
        sa.UniqueConstraint("email", name=op.f("uq_user_email")),
    )
    op.create_table(
        "user_session",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.user_id"],
            name=op.f("fk_user_session_user_id_user"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("session_id", name=op.f("pk_user_session")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_session_token_hash")),
    )
    op.create_index(
        op.f("ix_user_session_user_id"), "user_session", ["user_id"], unique=False
    )


def downgrade() -> None:
    """先删登录记录再删用户；这是删表操作，会删除这两张表中的数据。"""
    op.drop_index(op.f("ix_user_session_user_id"), table_name="user_session")
    op.drop_table("user_session")
    op.drop_table("user")
    # 扩展可能已由容器初始化，且会供其他业务表使用，因此回退不删除它。
