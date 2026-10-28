"""单次异步 LLM 调用：组装兼容接口请求，解析回答或工具请求。

由 Agent 调用，返回结构化 LLMResult；将网络与响应错误转换为业务异常。
本层记录调用元数据，不负责工具执行、数据库写入或 HTTP 状态映射。
"""

from dataclasses import dataclass, field
import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMToolCall:
    """模型提出的工具请求；arguments 保留原始 JSON，稍后由执行层校验。"""
    call_id: str
    name: str
    arguments: str


@dataclass
class LLMResult:
    """一次成功模型调用的结构化结果，供 Agent 使用并由路由持久化。

    工具请求时 answer 可以为 None；缺少 usage 时 Token 字段保持 None。
    它代表一次调用，不等于整个 Agent 已经完成回答。
    """
    answer: str | None
    model: str
    upstream_status: int
    latency_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    # 每个结果独享一个工具列表，避免不同模型调用共享可变默认对象。
    tool_calls: list[LLMToolCall] = field(default_factory=list)


class LLMRequestError(Exception):
    """携带失败模型名、分类、可用上游状态和耗时的统一模型异常边界。"""
    outcome: str

    def __init__(
        self,
        message: str,
        *,
        model: str,
        upstream_status: int | None,
        latency_ms: float,
    ) -> None:
        super().__init__(message)
        self.model = model
        self.upstream_status = upstream_status
        self.latency_ms = latency_ms


class LLMTimeoutError(LLMRequestError):
    """模型读取超时；由路由映射为 HTTP 504。"""
    outcome = "timeout"


class LLMConnectionError(LLMRequestError):
    """连接上游失败；由路由映射为 HTTP 503。"""
    outcome = "connection_error"


class LLMUpstreamError(LLMRequestError):
    """上游返回非成功 HTTP 状态；由路由映射为 HTTP 502。"""
    outcome = "upstream_error"


class LLMResponseError(LLMRequestError):
    """HTTP 响应存在，但 JSON 或所需字段不可用；由路由映射为 HTTP 502。"""
    outcome = "invalid_response"


async def generate_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    tools: list[dict] | None = None,
    additional_messages: list[dict] | None = None,
    *,
    system_prompt: str = "You are a helpful assistant.",
    memory_context: str = "",
) -> LLMResult:
    """执行一次异步模型请求，解析普通回答或待执行的工具请求。

    Args:
        message: 本轮用户问题。
        history: 旧会话消息，以正序插入系统指令和可选记忆参考之后。
        tools: 本轮允许模型选择的工具声明；None 表示不携带工具配置。
        additional_messages: Agent 本轮已产生的工具请求和工具结果消息。
        system_prompt: 本次调用的系统指令；默认用于普通聊天。
        memory_context: 独立记忆参考数据；为空时不增加消息，不修改 history。

    Returns:
        回答、工具请求及本次调用的状态、耗时和可选 Token 元数据。

    Raises:
        LLMTimeoutError: 上游读取超时。
        LLMConnectionError: 无法连接上游。
        LLMUpstreamError: 上游返回非成功 HTTP 状态。
        LLMResponseError: 响应无法解析为可用的模型结果。
    """
    if history is None:
        history = []

    if additional_messages is None:
        additional_messages = []

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    memory_messages = []
    if memory_context:
        memory_messages.append({
            "role": "user",
            "content": memory_context,
        })

    # 独立参考数据在历史之前；当前问题和工具交互保持原有顺序。
    payload = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            *memory_messages,
            *history,
            {
                "role": "user",
                "content": message,
            },
            *additional_messages,
        ],
        "stream": False,
    }

    if tools is not None:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    started_at = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )
            # HTTP 层成功只允许继续解析，不保证正文是合法或可用的模型结果。
            response.raise_for_status()
    except httpx.ReadTimeout as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000

        logger.warning(
            "LLM request failed model=%s status=unavailable "
            "latency_ms=%.2f error=timeout",
            settings.openai_model,
            latency_ms,
        )

        raise LLMTimeoutError(
            "LLM request timed out.",
            model=settings.openai_model,
            upstream_status=None,
            latency_ms=latency_ms,
        ) from exc

    except httpx.ConnectError as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000

        logger.warning(
            "LLM request failed model=%s status=unavailable "
            "latency_ms=%.2f error=connection",
            settings.openai_model,
            latency_ms,
        )

        raise LLMConnectionError(
            "LLM service unavailable.",
            model=settings.openai_model,
            upstream_status=None,
            latency_ms=latency_ms,
        ) from exc

    except httpx.HTTPStatusError as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000

        logger.warning(
            "LLM request failed model=%s status=%s "
            "latency_ms=%.2f error=upstream_status",
            settings.openai_model,
            response.status_code,
            latency_ms,
        )

        raise LLMUpstreamError(
            "LLM upstream request failed.",
            model=settings.openai_model,
            upstream_status=response.status_code,
            latency_ms=latency_ms,
        ) from exc

    try:
        # JSON 解析和必要字段提取放在同一边界，统一转换为 LLMResponseError。
        response_data = response.json()
        message_data = response_data["choices"][0]["message"]
        answer = message_data["content"]

        # 此处只解析“模型希望调用什么”，工具是否可执行由后续 Agent/工具层判断。
        tool_calls = [
            LLMToolCall(
                call_id=tool_call["id"],
                name=tool_call["function"]["name"],
                arguments=tool_call["function"]["arguments"],
            )
            for tool_call in message_data.get("tool_calls") or []
        ]
    except (json.JSONDecodeError, KeyError) as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000

        logger.warning(
            "LLM request failed model=%s status=%s "
            "latency_ms=%.2f error=invalid_response",
            settings.openai_model,
            response.status_code,
            latency_ms,
        )

        raise LLMResponseError(
            "LLM returned an invalid response.",
            model=settings.openai_model,
            upstream_status=response.status_code,
            latency_ms=latency_ms,
        ) from exc

    # usage 是可选观测数据；缺失时返回 None，不让一条有效回答因统计缺失而失败。
    usage = response_data.get("usage") or {}

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")

    latency_ms = (time.perf_counter() - started_at) * 1000

    # 只记录分类、状态、耗时和 Token，不记录消息正文、请求头或 API Key。
    logger.info(
        "LLM request succeeded model=%s status=%s latency_ms=%.2f "
        "prompt_tokens=%s completion_tokens=%s total_tokens=%s",
        settings.openai_model,
        response.status_code,
        latency_ms,
        prompt_tokens if prompt_tokens is not None else "unavailable",
        completion_tokens if completion_tokens is not None else "unavailable",
        total_tokens if total_tokens is not None else "unavailable",
    )

    return LLMResult(
        answer=answer,
        model=settings.openai_model,
        upstream_status=response.status_code,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        tool_calls=tool_calls,
    )
