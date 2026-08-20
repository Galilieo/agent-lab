from dataclasses import dataclass, field
import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMToolCall:
    call_id: str
    name: str
    arguments: str


@dataclass
class LLMResult:
    answer: str | None
    model: str
    upstream_status: int
    latency_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    tool_calls: list[LLMToolCall] = field(default_factory=list)


class LLMRequestError(Exception):
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
    outcome = "timeout"


class LLMConnectionError(LLMRequestError):
    outcome = "connection_error"


class LLMUpstreamError(LLMRequestError):
    outcome = "upstream_error"


class LLMResponseError(LLMRequestError):
    outcome = "invalid_response"


async def generate_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
    tools: list[dict] | None = None,
    additional_messages: list[dict] | None = None,
) -> LLMResult:
    if history is None:
        history = []

    if additional_messages is None:
        additional_messages = []

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant.",
            },
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
        response_data = response.json()
        message_data = response_data["choices"][0]["message"]
        answer = message_data["content"]

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

    usage = response_data.get("usage") or {}

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")

    latency_ms = (time.perf_counter() - started_at) * 1000

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
