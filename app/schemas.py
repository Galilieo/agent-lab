"""定义 HTTP 请求、响应与内部记忆提取结果的数据契约。

FastAPI 校验 HTTP 请求与响应；内部提取结果通过 model_validate 显式校验。
字段类型和长度限制保护输入形状；会话归属等业务规则由路由和数据库处理。
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    key: Literal[
        "answer_language",
        "explanation_style",
        "learning_goal",
        "tech_stack",
    ]
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
