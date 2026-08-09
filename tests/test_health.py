import httpx

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_llm_service_answer(monkeypatch) -> None:
    async def fake_generate_reply(message: str) -> str:
        assert message == "你好"
        return "模拟模型回答"

    monkeypatch.setattr(
        "app.main.generate_reply",
        fake_generate_reply,
    )

    response = client.post(
        "/chat",
        json={"conversation_id": "test-001", "message": "你好"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "test-001",
        "answer": "模拟模型回答",
    }


def test_chat_rejects_empty_message() -> None:
    payload = {
        "conversation_id": "test-001",
        "message": "",
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "message"]


def test_chat_rejects_missing_message() -> None:
    payload = {
        "conversation_id": "test-001",
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "message"]


def test_chat_rejects_non_string_message() -> None:
    payload = {
        "conversation_id": "test-001",
        "message": 123,
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "message"]
    assert error["type"] == "string_type"


def test_chat_rejects_closed_conversation() -> None:
    payload = {
        "conversation_id": "closed-001",
        "message": "你好",
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "Conversation is closed."}


def test_chat_configures_extended_llm_timeout(monkeypatch) -> None:
    observed = {}

    class FakeAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            observed["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "id": "test-completion",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "index": 0,
                            "message": {
                                "content": "模拟模型回答",
                                "reasoning_content": None,
                                "role": "assistant",
                                "tool_calls": [],
                            },
                            "logprobs": None,
                        }
                    ],
                    "created": 0,
                    "model": "deepseek-v4-flash",
                    "system_fingerprint": "test-fingerprint",
                    "object": "chat.completion",
                    "usage": {
                        "completion_tokens": 4,
                        "prompt_tokens": 8,
                        "prompt_cache_hit_tokens": 0,
                        "prompt_cache_miss_tokens": 8,
                        "total_tokens": 12,
                        "completion_tokens_details": {
                            "reasoning_tokens": 0,
                        },
                    },
                },
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        FakeAsyncClient,
    )

    response = client.post(
        "/chat",
        json={"conversation_id": "test-001", "message": "你好"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "模拟模型回答"
    assert observed["timeout"] == 60.0


def test_chat_returns_gateway_timeout_when_llm_times_out(monkeypatch) -> None:
    class TimeoutAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            raise httpx.ReadTimeout("DeepSeek response timed out.")

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        TimeoutAsyncClient,
    )

    error_client = TestClient(
        app,
        raise_server_exceptions=False,
    )

    response = error_client.post(
        "/chat",
        json={"conversation_id": "test-001", "message": "你好"},
    )

    assert response.status_code == 504
    assert response.json() == {
        "detail": "LLM request timed out.",
    }


def test_chat_returns_service_unavailable_when_llm_connection_fails(monkeypatch) -> None:
    class ConnectionFailingAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            raise httpx.ConnectError("Unable to connect to DeepSeek.")

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        ConnectionFailingAsyncClient,
    )

    error_client = TestClient(
        app,
        raise_server_exceptions=False,
    )

    response = error_client.post(
        "/chat",
        json={"conversation_id": "test-001", "message": "你好"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "LLM service unavailable.",
    }


def test_chat_returns_bad_gateway_when_llm_returns_error_status(monkeypatch) -> None:
    class UpstreamErrorAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            return httpx.Response(
                401,
                request=httpx.Request("POST", url),
                json={
                    "error": {
                        "message": "Invalid API key",
                    }
                },
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        UpstreamErrorAsyncClient,
    )

    error_client = TestClient(
        app,
        raise_server_exceptions=False,
    )

    response = error_client.post(
        "/chat",
        json={"conversation_id": "test-001", "message": "你好"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "LLM upstream request failed.",
    }
