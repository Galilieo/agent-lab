import httpx

from app.config import settings


class LLMTimeoutError(Exception):
    pass


class LLMConnectionError(Exception):
    pass


class LLMUpstreamError(Exception):
    pass


async def generate_reply(message: str) -> str:
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
            {
                "role": "user",
                "content": message,
            },
        ],
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
    except httpx.ReadTimeout as exc:
        raise LLMTimeoutError("LLM request timed out.") from exc
    except httpx.ConnectError as exc:
        raise LLMConnectionError("LLM service unavailable.") from exc
    except httpx.HTTPStatusError as exc:
        raise LLMUpstreamError("LLM upstream request failed.") from exc

    response_data = response.json()
    return response_data["choices"][0]["message"]["content"]
