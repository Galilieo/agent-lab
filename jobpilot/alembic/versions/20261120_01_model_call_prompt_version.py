"""模型调用记录增加提示词版本，修复重发时记录两份提示词的版本。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261120_01"
down_revision: str | Sequence[str] | None = "20261118_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """允许为空：本迁移之前的调用没有记录版本。"""
    op.add_column("model_call", sa.Column("prompt_version", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("model_call", "prompt_version")
