"""声明账号、业务运行、模型调用和经历事实库的 ORM 映射。"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates

from jobpilot.db.base import Base


def normalize_email(email: str) -> str:
    """将邮箱转为 JobPilot 用于存储和查找账号的登录标识。"""
    return email.lower()


class User(Base):
    """保存账号身份及待删除状态；密码由登录模块哈希后写入。"""

    __tablename__ = "user_account"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(320))
    hashed_password: Mapped[str] = mapped_column(Text)
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    __table_args__ = (
        Index("uq_user_account_email_lower", func.lower(email), unique=True),
    )

    @validates("email")
    def _normalize_email(self, key: str, value: str) -> str:
        """账号创建和修改都复用登录、恢复时的规范化规则。"""
        return normalize_email(value)


class UserSession(Base):
    """保存登录 token 的 SHA-256 十六进制摘要、归属用户及到期时间。"""

    __tablename__ = "user_session"

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_account.user_id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RunStatus(StrEnum):
    """持久化的运行状态，等待确认时仍可继续执行。"""

    RUNNING = "running"
    WAITING_CONFIRMATION = "waiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"


class CallOutcome(StrEnum):
    """一次模型发送的结果；unknown 表示没拿到响应，用量也无从得知。"""

    UNKNOWN = "unknown"
    SUCCESS = "success"
    INVALID_OUTPUT = "invalid_output"
    HTTP_ERROR = "http_error"


class AiRun(Base):
    """记录一次业务运行，供产物、模型请求和检查点关联。"""

    __tablename__ = "ai_run"
    __table_args__ = (
        UniqueConstraint("run_id", "user_id"),
        CheckConstraint(
            "kind IN ('parse_resume', 'parse_jd', 'match', 'tailor', 'agent')",
            name="ck_ai_run_kind",
        ),
        CheckConstraint(
            "status IN ('running', 'waiting_confirmation', 'succeeded', "
            "'failed', 'cancelled', 'budget_exhausted')",
            name="ck_ai_run_status",
        ),
        CheckConstraint(
            "(status IN ('running', 'waiting_confirmation')) = (finished_at IS NULL)",
            name="ck_ai_run_finished_at",
        ),
        Index("ix_ai_run_user_id_started_at", "user_id", "started_at"),
        # 运行使用的事实库版本必须属于同一用户。
        ForeignKeyConstraint(
            ["fact_set_id", "user_id"],
            ["fact_set.fact_set_id", "fact_set.user_id"],
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.user_id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), server_default="running")
    thread_id: Mapped[str | None] = mapped_column(Text)
    fact_set_id: Mapped[UUID | None] = mapped_column(Uuid)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ModelCall(Base):
    """记录一次实际模型请求的结果和用量，运行删除后匿名保留。"""

    __tablename__ = "model_call"
    __table_args__ = (
        ForeignKeyConstraint(
            ["run_id", "user_id"],
            ["ai_run.run_id", "ai_run.user_id"],
            ondelete="SET NULL",
        ),
        CheckConstraint(
            "(run_id IS NULL) = (user_id IS NULL)", name="ck_model_call_run_ownership"
        ),
        CheckConstraint(
            "outcome <> 'unknown' OR "
            "(prompt_tokens IS NULL AND completion_tokens IS NULL)",
            name="ck_model_call_unknown_usage",
        ),
        CheckConstraint("latency_ms >= 0", name="ck_model_call_latency_ms"),
        CheckConstraint("prompt_tokens >= 0", name="ck_model_call_prompt_tokens"),
        CheckConstraint(
            "completion_tokens >= 0", name="ck_model_call_completion_tokens"
        ),
        Index("ix_model_call_run_id_user_id", "run_id", "user_id"),
        Index("ix_model_call_user_id_created_at", "user_id", "created_at"),
    )

    call_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID | None] = mapped_column(Uuid)
    user_id: Mapped[UUID | None] = mapped_column(Uuid)
    purpose: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(Text)
    # 如 parse_jd@3；修复重发记为 parse_jd@3+repair_json@1。旧记录为空。
    prompt_version: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[int | None]
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]


class FactKind(StrEnum):
    """原子事实的类型：做了什么、用了什么技术、结果或数字、角色。"""

    ACTION = "action"
    TECHNOLOGY = "technology"
    RESULT = "result"
    ROLE = "role"


class Responsibility(StrEnum):
    """职责程度；教育、技能、获奖等不适用的经历记为 na。"""

    LEAD = "lead"
    OWN = "own"
    PARTICIPATE = "participate"
    NA = "na"


class FactSource(StrEnum):
    """事实来源：从简历解析，或用户手动补充与纠正。"""

    RESUME = "resume"
    USER = "user"


class ResumeDocument(Base):
    """用户核对后的简历全文；事实的原文片段和位置都以这里的 raw_text 为准。

    上传的原文件解析后不保存。上传时间用继承的 created_at。
    """

    __tablename__ = "resume_document"
    __table_args__ = (
        # 供事实用 (source_doc_id, user_id) 引用同一用户的文档。
        UniqueConstraint("doc_id", "user_id"),
        Index("ix_resume_document_user_id_created_at", "user_id", "created_at"),
    )

    doc_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.user_id", ondelete="CASCADE")
    )
    filename: Mapped[str | None] = mapped_column(Text)  # 粘贴文本时为空
    raw_text: Mapped[str] = mapped_column(Text)
    sections_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default=sql_text("'[]'::jsonb")
    )


class FactSet(Base):
    """已发布的事实库完整快照，同一用户的版本号从 1 递增。"""

    __tablename__ = "fact_set"
    __table_args__ = (
        UniqueConstraint("user_id", "version"),
        # 供事实、草稿和运行用 (fact_set_id, user_id) 引用同一用户的版本。
        UniqueConstraint("fact_set_id", "user_id"),
        CheckConstraint("version >= 1", name="ck_fact_set_version"),
    )

    fact_set_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.user_id", ondelete="CASCADE")
    )
    version: Mapped[int]


class Fact(Base):
    """已确认的原子事实。只追加：发布后不修改、不单独删除，数据库触发器拒绝 UPDATE。

    fact_id 标识某个版本里的一行；lineage_id 标识跨版本的同一条事实，修订时沿用。
    来自简历的事实必须带原文片段与位置，且原文校验已通过。
    """

    __tablename__ = "fact"
    __table_args__ = (
        # 组合外键：事实与版本必须属于同一用户。没有 SET NULL，因为它会变成 UPDATE。
        ForeignKeyConstraint(
            ["fact_set_id", "user_id"],
            ["fact_set.fact_set_id", "fact_set.user_id"],
            ondelete="CASCADE",
        ),
        # 引用原文的外键延迟到提交时检查：删除账号时原文和事实在同一事务里被级联删除，
        # 立即检查会先看到「原文仍被引用」而失败；单独删除仍被引用的原文依然会被拒绝。
        ForeignKeyConstraint(
            ["source_doc_id", "user_id"],
            ["resume_document.doc_id", "resume_document.user_id"],
            deferrable=True,
            initially="DEFERRED",
        ),
        UniqueConstraint("user_id", "fact_set_id", "lineage_id"),
        CheckConstraint(
            "kind IN ('action', 'technology', 'result', 'role')", name="ck_fact_kind"
        ),
        CheckConstraint(
            "responsibility IN ('lead', 'own', 'participate', 'na')",
            name="ck_fact_responsibility",
        ),
        CheckConstraint(
            "(source = 'resume' AND source_doc_id IS NOT NULL "
            "AND source_quote IS NOT NULL AND span_start IS NOT NULL "
            "AND span_end IS NOT NULL AND quote_verified) "
            "OR (source = 'user' AND source_doc_id IS NULL "
            "AND source_quote IS NULL AND span_start IS NULL AND span_end IS NULL)",
            name="ck_fact_source",
        ),
        CheckConstraint(
            "span_start IS NULL OR (span_start >= 0 AND span_start < span_end)",
            name="ck_fact_span",
        ),
    )

    fact_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    fact_set_id: Mapped[UUID] = mapped_column(Uuid)
    user_id: Mapped[UUID] = mapped_column(Uuid)
    lineage_id: Mapped[UUID] = mapped_column(Uuid)
    experience: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(16))
    responsibility: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    has_number: Mapped[bool]
    source: Mapped[str] = mapped_column(String(16))
    source_doc_id: Mapped[UUID | None] = mapped_column(Uuid)
    source_quote: Mapped[str | None] = mapped_column(Text)
    # raw_text[span_start:span_end] == source_quote；按核对稿计算，不按脱敏文本。
    span_start: Mapped[int | None]
    span_end: Mapped[int | None]
    quote_verified: Mapped[bool] = mapped_column(server_default=sql_text("false"))


class FactDraft(Base):
    """每个用户一份发布前的草稿：待确认、修改和删除的事实都放在 items_json。

    base_fact_set_id 记录草稿基于哪个版本；发布时若最新版本已不是它，返回冲突。
    """

    __tablename__ = "fact_draft"
    __table_args__ = (
        ForeignKeyConstraint(
            ["base_fact_set_id", "user_id"],
            ["fact_set.fact_set_id", "fact_set.user_id"],
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.user_id", ondelete="CASCADE"), primary_key=True
    )
    base_fact_set_id: Mapped[UUID | None] = mapped_column(Uuid)  # 首次发布前为空
    items_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default=sql_text("'[]'::jsonb")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
