"""声明账号、业务运行和模型调用的 ORM 映射。"""

from datetime import datetime
from enum import StrEnum
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
    )

    run_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_account.user_id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), server_default="running")
    thread_id: Mapped[str | None] = mapped_column(Text)
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
    outcome: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[int | None]
    prompt_tokens: Mapped[int | None]
    completion_tokens: Mapped[int | None]
