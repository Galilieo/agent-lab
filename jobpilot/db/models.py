"""声明用户与登录记录的 ORM 映射；导入模型不会自动创建数据库表。"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, true
from sqlalchemy.orm import Mapped, mapped_column

from jobpilot.db.base import Base


class User(Base):
    """保存账号身份及待删除状态；密码由登录模块哈希后写入。"""

    __tablename__ = "user"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True)
    hashed_password: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true()
    )
    deletion_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class UserSession(Base):
    """保存登录 token 的 SHA-256 十六进制摘要、归属用户及到期时间。"""

    __tablename__ = "user_session"

    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user.user_id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
