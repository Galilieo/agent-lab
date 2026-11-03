"""通过模型回调收集单轮 Agent 的调用观察记录。

记录模型步骤的耗时、可用 Token 数和异常类型，不保存消息正文或密钥。
记录保存在独立对象中；Agent 中途失败时，持有该对象的调用方仍可读取。
这不是数据库写入器，也不承诺提供上游 HTTP 状态或替代原生 LLMResult。
"""

from dataclasses import dataclass
import time
from typing import Literal
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult as LangChainLLMResult


@dataclass
class ModelCallObservation:
    """一次框架模型步骤的观察记录；计时覆盖回调起止之间的模型步骤。"""

    run_id: UUID
    outcome: Literal["succeeded", "failed"]
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    error_type: str | None = None


class ModelCallRecorder(AsyncCallbackHandler):
    """每次 Agent 请求独立创建的记录器，按模型 run_id 配对开始与结束。"""

    def __init__(self) -> None:
        self.records: list[ModelCallObservation] = []
        self._started_at: dict[UUID, float] = {}

    async def on_chat_model_start(
        self, serialized, messages, *, run_id: UUID, **kwargs
    ) -> None:
        """模型调用开始时记录计时点，不保存传入的消息或序列化配置。"""
        self._started_at[run_id] = time.perf_counter()

    async def on_llm_end(
        self, response: LangChainLLMResult, *, run_id: UUID, **kwargs
    ) -> None:
        """模型正常返回时，记录耗时及本次 AIMessage 中的可用 Token 数。"""
        started_at = self._started_at.pop(run_id)
        message = response.generations[0][0].message
        usage = message.usage_metadata or {}
        self.records.append(ModelCallObservation(
            run_id=run_id,
            outcome="succeeded",
            latency_ms=(time.perf_counter() - started_at) * 1000,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            total_tokens=usage.get("total_tokens"),
        ))

    async def on_llm_error(
        self, error: BaseException, *, run_id: UUID, **kwargs
    ) -> None:
        """模型失败时记录耗时和异常类名，不复制异常正文。"""
        started_at = self._started_at.pop(run_id)

        self.records.append(ModelCallObservation(
            run_id=run_id,
            outcome="failed",
            latency_ms=(time.perf_counter() - started_at) * 1000,
            error_type=type(error).__name__,
        ))
