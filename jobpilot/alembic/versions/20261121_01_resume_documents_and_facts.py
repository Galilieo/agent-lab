"""创建简历原文、事实库版本、事实和草稿表；事实只追加，触发器拒绝 UPDATE。"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "20261121_01"
down_revision: str | Sequence[str] | None = "20261120_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def upgrade() -> None:
    """先建被引用的原文和版本，再建事实与草稿，最后给运行补上版本关联。

    不级联的组合外键都延迟到提交时检查，账号删除时级联顺序不会误报仍被引用。
    """
    op.create_table(
        "resume_document",
        sa.Column("doc_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column(
            "sections_json",
            JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        _created_at(),
        sa.PrimaryKeyConstraint("doc_id", name=op.f("pk_resume_document")),
        sa.UniqueConstraint(
            "doc_id", "user_id", name=op.f("uq_resume_document_doc_id")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.user_id"],
            name=op.f("fk_resume_document_user_id_user_account"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_resume_document_user_id_created_at",
        "resume_document",
        ["user_id", "created_at"],
    )

    op.create_table(
        "fact_set",
        sa.Column("fact_set_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("fact_set_id", name=op.f("pk_fact_set")),
        sa.UniqueConstraint("user_id", "version", name=op.f("uq_fact_set_user_id")),
        sa.UniqueConstraint(
            "fact_set_id", "user_id", name=op.f("uq_fact_set_fact_set_id")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.user_id"],
            name=op.f("fk_fact_set_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("version >= 1", name="ck_fact_set_version"),
    )

    op.create_table(
        "fact",
        sa.Column("fact_id", sa.Uuid(), nullable=False),
        sa.Column("fact_set_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lineage_id", sa.Uuid(), nullable=False),
        sa.Column("experience", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("responsibility", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("has_number", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("source_doc_id", sa.Uuid(), nullable=True),
        sa.Column("source_quote", sa.Text(), nullable=True),
        sa.Column("span_start", sa.Integer(), nullable=True),
        sa.Column("span_end", sa.Integer(), nullable=True),
        sa.Column(
            "quote_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        _created_at(),
        sa.PrimaryKeyConstraint("fact_id", name=op.f("pk_fact")),
        sa.ForeignKeyConstraint(
            ["fact_set_id", "user_id"],
            ["fact_set.fact_set_id", "fact_set.user_id"],
            name=op.f("fk_fact_fact_set_id_fact_set"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_doc_id", "user_id"],
            ["resume_document.doc_id", "resume_document.user_id"],
            name=op.f("fk_fact_source_doc_id_resume_document"),
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.UniqueConstraint(
            "user_id", "fact_set_id", "lineage_id", name=op.f("uq_fact_user_id")
        ),
        sa.CheckConstraint(
            "kind IN ('action', 'technology', 'result', 'role')", name="ck_fact_kind"
        ),
        sa.CheckConstraint(
            "responsibility IN ('lead', 'own', 'participate', 'na')",
            name="ck_fact_responsibility",
        ),
        sa.CheckConstraint(
            "(source = 'resume' AND source_doc_id IS NOT NULL "
            "AND source_quote IS NOT NULL AND span_start IS NOT NULL "
            "AND span_end IS NOT NULL AND quote_verified) "
            "OR (source = 'user' AND source_doc_id IS NULL "
            "AND source_quote IS NULL AND span_start IS NULL AND span_end IS NULL)",
            name="ck_fact_source",
        ),
        sa.CheckConstraint(
            "span_start IS NULL OR (span_start >= 0 AND span_start < span_end)",
            name="ck_fact_span",
        ),
    )
    # 已发布的事实只追加：任何 UPDATE 都报错。删除仍允许，供账号彻底删除时级联。
    op.execute("""
        CREATE FUNCTION reject_fact_update() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'fact rows are append-only; publish a new fact_set instead';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER fact_append_only BEFORE UPDATE ON fact
        FOR EACH ROW EXECUTE FUNCTION reject_fact_update()
    """)

    op.create_table(
        "fact_draft",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("base_fact_set_id", sa.Uuid(), nullable=True),
        sa.Column(
            "items_json", JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        _created_at(),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_fact_draft")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_account.user_id"],
            name=op.f("fk_fact_draft_user_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["base_fact_set_id", "user_id"],
            ["fact_set.fact_set_id", "fact_set.user_id"],
            name=op.f("fk_fact_draft_base_fact_set_id_fact_set"),
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    op.add_column("ai_run", sa.Column("fact_set_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_ai_run_fact_set_id_fact_set"),
        "ai_run",
        "fact_set",
        ["fact_set_id", "user_id"],
        ["fact_set_id", "user_id"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_ai_run_fact_set_id_fact_set"), "ai_run", type_="foreignkey"
    )
    op.drop_column("ai_run", "fact_set_id")
    op.drop_table("fact_draft")
    op.execute("DROP TRIGGER fact_append_only ON fact")
    op.execute("DROP FUNCTION reject_fact_update()")
    op.drop_table("fact")
    op.drop_table("fact_set")
    op.drop_index("ix_resume_document_user_id_created_at", "resume_document")
    op.drop_table("resume_document")
