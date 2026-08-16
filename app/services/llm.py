from dataclasses import dataclass
import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    answer: str
    model: str
    upstream_status: int
    latency_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


class LLMTimeoutError(Exception):
    pass


class LLMConnectionError(Exception):
    pass


class LLMUpstreamError(Exception):
    pass


class LLMResponseError(Exception):
    pass


async def generate_reply(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> LLMResult:
    if history is None:
        history = []

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
        ],
        "stream": False,
    }

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

        raise LLMTimeoutError("LLM request timed out.") from exc

    except httpx.ConnectError as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000

        logger.warning(
            "LLM request failed model=%s status=unavailable "
            "latency_ms=%.2f error=connection",
            settings.openai_model,
            latency_ms,
        )

        raise LLMConnectionError("LLM service unavailable.") from exc

    except httpx.HTTPStatusError as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000

        logger.warning(
            "LLM request failed model=%s status=%s "
            "latency_ms=%.2f error=upstream_status",
            settings.openai_model,
            response.status_code,
            latency_ms,
        )

        raise LLMUpstreamError("LLM upstream request failed.") from exc

    try:
        response_data = response.json()
        answer = response_data["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError) as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000

        logger.warning(
            "LLM request failed model=%s status=%s "
            "latency_ms=%.2f error=invalid_response",
            settings.openai_model,
            response.status_code,
            latency_ms,
        )

        raise LLMResponseError("LLM returned an invalid response.") from exc

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
    )
