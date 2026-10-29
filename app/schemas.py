"""定义 HTTP 请求、响应与内部记忆提取结果的数据契约。

FastAPI 校验 HTTP 请求与响应；内部提取结果通过 model_validate 显式校验。
字段类型和长度限制保护输入形状；会话归属等业务规则由路由和数据库处理。
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


MemoryKey = Literal[
    "answer_language", "explanation_style", "learning_goal", "tech_stack",
]


# 健康检查的固定响应；服务可响应不代表模型服务可用。
class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


# 聊天输入契约；user_id 可省略，归属是否一致由业务链路验证。
class ChatRequest(BaseModel):
    conversation_id: str = Field(min_length=1)
    message: str = Field(min_length=1)
    user_id: str | None = Field(default=None, min_length=1)


# 聊天成功响应；只暴露会话标识和最终回答，不暴露内部调用记录。
class ChatResponse(BaseModel):
    conversation_id: str
    answer: str


class MemoryCandidate(BaseModel):
    """约束模型提出的单条记忆，不接受身份或来源字段。"""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    scope: Literal["user", "conversation"]
    key: MemoryKey
    value: str = Field(min_length=1)


class MemoryExtractionResult(BaseModel):
    """约束提取动作与候选列表之间的关系。"""

    model_config = ConfigDict(extra="forbid")

    action: Literal["upsert", "skip"]
    memories: list[MemoryCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_action(self) -> Self:
        # 字段校验完成后，再检查动作与列表是否匹配。
        if self.action == "upsert" and not self.memories:
            raise ValueError("upsert requires at least one memory")

        if self.action == "skip" and self.memories:
            raise ValueError("skip cannot contain memories")

        return self


class MemoryQueryRequest(BaseModel):
    """管理已有会话可见的记忆，不接受调用方指定任意 scope_id。"""

    # 标识符与 ChatRequest 一样原样保留，避免管理时指向另一组已存在的 ID。
    model_config = ConfigDict(extra="forbid")

    conversation_id: str = Field(min_length=1)
    user_id: str | None = Field(default=None, min_length=1)


class MemoryDeleteRequest(MemoryQueryRequest):
    """明确指定某一 key 和删除范围，不提供隐式全量删除默认值。"""

    key: MemoryKey
    target: Literal["user", "conversation", "all"]

    @model_validator(mode="after")
    def validate_user_target(self) -> Self:
        if self.target in ("user", "all") and self.user_id is None:
            raise ValueError("User-scoped deletion requires user_id.")
        return self


class MemoryRecord(BaseModel):
    """查看原始记录及来源，不表示合并后本轮一定使用它。"""

    scope: Literal["user", "conversation"]
    scope_id: str
    key: str
    value: str
    source_message_id: int
    updated_at: str


class MemoryQueryResponse(BaseModel):
    memories: list[MemoryRecord]


class MemoryDeleteResponse(BaseModel):
    deleted_count: int = Field(ge=0)
