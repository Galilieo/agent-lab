import asyncio
import logging

import httpx
import pytest

from fastapi.testclient import TestClient

from app.database import create_connection
from app.main import app
from app.services.llm import LLMResult, generate_reply

@pytest.fixture
def database_path(monkeypatch, tmp_path):
    path = tmp_path / "agent-lab-test.db"
    monkeypatch.setattr(
        "app.main.settings.database_path",
        str(path),
    )
    return path


@pytest.fixture
def client(database_path):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def error_client(database_path):
    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as test_client:
        yield test_client


def test_app_startup_initializes_database_schema_without_chat_request(
    database_path,
) -> None:
    with TestClient(app):
        pass

    connection = create_connection(str(database_path))

    try:
        table_names = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                    AND name IN (
                        'conversation',
                        'message',
                        'model_call'
                    )
                """
            ).fetchall()
        }
    finally:
        connection.close()

    assert table_names == {
        "conversation",
        "message",
        "model_call",
    }


def test_health_returns_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_persists_assistant_message_after_successful_llm_call(
    monkeypatch,
    database_path,
    client,
) -> None:
    observed_calls = []

    async def fake_generate_reply(
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> LLMResult:
        connection = create_connection(str(database_path))

        try:
            persisted_messages = connection.execute(
                """
                SELECT role, content
                FROM message
                WHERE conversation_id = ?
                ORDER BY message_id
                """,
                ("conversation-c",),
            ).fetchall()
        finally:
            connection.close()

        observed_calls.append(
            {
                "message": message,
                "history": history,
                "persisted_messages": persisted_messages,
            }
        )
        return LLMResult(
            answer="模拟模型回答",
            model="fake-model",
            upstream_status=200,
            latency_ms=10.0,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
        )

    monkeypatch.setattr(
        "app.main.generate_reply",
        fake_generate_reply,
    )

    first_response = client.post(
        "/chat",
        json={
            "conversation_id": "conversation-c",
            "message": "我叫小宇",
        },
    )
    second_response = client.post(
        "/chat",
        json={
            "conversation_id": "conversation-c",
            "message": "我叫什么？",
        },
    )

    assert first_response.status_code == 200
    assert first_response.json() == {
        "conversation_id": "conversation-c",
        "answer": "模拟模型回答",
    }
    assert second_response.status_code == 200
    assert second_response.json() == {
        "conversation_id": "conversation-c",
        "answer": "模拟模型回答",
    }
    assert observed_calls == [
        {
            "message": "我叫小宇",
            "history": [],
            "persisted_messages": [
                ("user", "我叫小宇"),
            ],
        },
        {
            "message": "我叫什么？",
            "history": [
                {
                    "role": "user",
                    "content": "我叫小宇",
                },
                {
                    "role": "assistant",
                    "content": "模拟模型回答",
                },
            ],
            "persisted_messages": [
                ("user", "我叫小宇"),
                ("assistant", "模拟模型回答"),
                ("user", "我叫什么？"),
            ],
        },
    ]

    connection = create_connection(str(database_path))

    try:
        conversation = connection.execute(
            """
            SELECT conversation_id, status
            FROM conversation
            WHERE conversation_id = ?
            """,
            ("conversation-c",),
        ).fetchone()
        messages = connection.execute(
            """
            SELECT role, content
            FROM message
            WHERE conversation_id = ?
            ORDER BY message_id
            """,
            ("conversation-c",),
        ).fetchall()
        model_calls = connection.execute(
            """
            SELECT
                request_message.role,
                request_message.content,
                response_message.role,
                response_message.content,
                model_call.model,
                model_call.outcome,
                model_call.upstream_status,
                model_call.latency_ms,
                model_call.prompt_tokens,
                model_call.completion_tokens,
                model_call.total_tokens
            FROM model_call
            JOIN message AS request_message
                ON request_message.conversation_id = model_call.conversation_id
                AND request_message.message_id = model_call.request_message_id
            JOIN message AS response_message
                ON response_message.conversation_id = model_call.conversation_id
                AND response_message.message_id = model_call.response_message_id
            WHERE model_call.conversation_id = ?
            ORDER BY model_call.model_call_id
            """,
            ("conversation-c",),
        ).fetchall()
    finally:
        connection.close()

    assert conversation == ("conversation-c", "active")
    assert messages == [
        ("user", "我叫小宇"),
        ("assistant", "模拟模型回答"),
        ("user", "我叫什么？"),
        ("assistant", "模拟模型回答"),
    ]
    assert model_calls == [
        (
            "user",
            "我叫小宇",
            "assistant",
            "模拟模型回答",
            "fake-model",
            "succeeded",
            200,
            10.0,
            None,
            None,
            None,
        ),
        (
            "user",
            "我叫什么？",
            "assistant",
            "模拟模型回答",
            "fake-model",
            "succeeded",
            200,
            10.0,
            None,
            None,
            None,
        ),
    ]


def test_chat_rejects_empty_message(client) -> None:
    payload = {
        "conversation_id": "test-001",
        "message": "",
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "message"]


def test_chat_rejects_missing_message(client) -> None:
    payload = {
        "conversation_id": "test-001",
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "message"]


def test_chat_rejects_non_string_message(client) -> None:
    payload = {
        "conversation_id": "test-001",
        "message": 123,
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "message"]
    assert error["type"] == "string_type"


def test_chat_rejects_closed_conversation(client) -> None:
    payload = {
        "conversation_id": "closed-001",
        "message": "你好",
    }

    response = client.post("/chat", json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "Conversation is closed."}


def test_generate_reply_returns_structured_result_and_includes_history(
    monkeypatch,
) -> None:
    observed = {}

    class FakeAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            observed["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed["messages"] = json["messages"]

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
    monkeypatch.setattr(
        "app.services.llm.settings.openai_model",
        "deepseek-v4-flash",
    )

    result = asyncio.run(
        generate_reply(
            message="我叫什么？",
            history=[
                {"role": "user", "content": "我叫小宇"},
                {"role": "assistant", "content": "记住了"},
            ],
        )
    )

    assert result.answer == "模拟模型回答"
    assert result.model == "deepseek-v4-flash"
    assert result.upstream_status == 200
    assert result.latency_ms >= 0
    assert result.prompt_tokens == 8
    assert result.completion_tokens == 4
    assert result.total_tokens == 12
    assert observed["messages"] == [
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "我叫小宇",
        },
        {
            "role": "assistant",
            "content": "记住了",
        },
        {
            "role": "user",
            "content": "我叫什么？",
        },
    ]
    assert observed["timeout"] == 60.0


def test_chat_logs_and_returns_gateway_timeout_when_llm_times_out(
    monkeypatch,
    caplog,
    database_path,
    error_client,
) -> None:
    observed = {}

    class TimeoutAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed["model"] = json["model"]
            raise httpx.ReadTimeout("DeepSeek response timed out.")

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        TimeoutAsyncClient,
    )

    with caplog.at_level(logging.WARNING, logger="app.services.llm"):
        response = error_client.post(
            "/chat",
            json={"conversation_id": "test-001", "message": "你好"},
        )

    connection = create_connection(str(database_path))

    try:
        failed_model_calls = connection.execute(
            """
            SELECT
                request_message.role,
                request_message.content,
                model_call.response_message_id,
                model_call.model,
                model_call.outcome,
                model_call.upstream_status,
                model_call.latency_ms,
                model_call.prompt_tokens,
                model_call.completion_tokens,
                model_call.total_tokens
            FROM model_call
            JOIN message AS request_message
                ON request_message.conversation_id = model_call.conversation_id
                AND request_message.message_id = model_call.request_message_id
            WHERE model_call.conversation_id = ?
            ORDER BY model_call.model_call_id
            """,
            ("test-001",),
        ).fetchall()
    finally:
        connection.close()

    log_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.services.llm"
    ]

    assert response.status_code == 504
    assert response.json() == {
        "detail": "LLM request timed out.",
    }

    assert len(log_messages) == 1
    assert f"model={observed['model']}" in log_messages[0]
    assert "status=unavailable" in log_messages[0]
    assert "latency_ms=" in log_messages[0]
    assert "error=timeout" in log_messages[0]
    assert len(failed_model_calls) == 1
    failed_model_call = failed_model_calls[0]

    assert failed_model_call[:6] == (
        "user",
        "你好",
        None,
        observed["model"],
        "timeout",
        None,
    )
    assert failed_model_call[6] >= 0
    assert failed_model_call[7:] == (
        None,
        None,
        None,
    )


def test_chat_returns_service_unavailable_when_llm_connection_fails(
    monkeypatch,
    caplog,
    error_client,
) -> None:
    observed = {}

    class ConnectionFailingAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed["model"] = json["model"]
            raise httpx.ConnectError("Unable to connect to DeepSeek.")

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        ConnectionFailingAsyncClient,
    )

    with caplog.at_level(logging.WARNING, logger="app.services.llm"):
        response = error_client.post(
            "/chat",
            json={"conversation_id": "test-001", "message": "你好"},
        )

    log_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.services.llm"
    ]

    assert response.status_code == 503
    assert response.json() == {
        "detail": "LLM service unavailable.",
    }

    assert len(log_messages) == 1
    assert f"model={observed['model']}" in log_messages[0]
    assert "status=unavailable" in log_messages[0]
    assert "latency_ms=" in log_messages[0]
    assert "error=connection" in log_messages[0]


def test_chat_returns_bad_gateway_when_llm_returns_error_status(
    monkeypatch,
    caplog,
    error_client,
) -> None:
    observed = {}

    class UpstreamErrorAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed["model"] = json["model"]
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

    with caplog.at_level(logging.WARNING, logger="app.services.llm"):
        response = error_client.post(
            "/chat",
            json={"conversation_id": "test-001", "message": "你好"},
        )

    log_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.services.llm"
    ]

    assert response.status_code == 502
    assert response.json() == {
        "detail": "LLM upstream request failed.",
    }

    assert len(log_messages) == 1
    assert f"model={observed['model']}" in log_messages[0]
    assert "status=401" in log_messages[0]
    assert "latency_ms=" in log_messages[0]
    assert "error=upstream_status" in log_messages[0]


def test_chat_returns_bad_gateway_when_llm_returns_invalid_json(
    monkeypatch,
    caplog,
    error_client,
) -> None:
    observed = {}

    class InvalidJsonAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed["model"] = json["model"]
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                content=b"this is not json",
                headers={"Content-Type": "application/json"},
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        InvalidJsonAsyncClient,
    )

    with caplog.at_level(logging.WARNING, logger="app.services.llm"):
        response = error_client.post(
            "/chat",
            json={"conversation_id": "test-001", "message": "你好"},
        )

    log_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.services.llm"
    ]

    assert response.status_code == 502
    assert response.json() == {
        "detail": "LLM returned an invalid response.",
    }

    assert len(log_messages) == 1
    assert f"model={observed['model']}" in log_messages[0]
    assert "status=200" in log_messages[0]
    assert "latency_ms=" in log_messages[0]
    assert "error=invalid_response" in log_messages[0]


def test_chat_returns_bad_gateway_when_llm_response_has_no_choices(
    monkeypatch,
    error_client,
) -> None:
    class MissingChoicesAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

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
                    "object": "chat.completion",
                },
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        MissingChoicesAsyncClient,
    )

    response = error_client.post(
        "/chat",
        json={"conversation_id": "test-001", "message": "你好"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "LLM returned an invalid response.",
    }


def test_chat_returns_bad_gateway_when_llm_response_has_no_content(
    monkeypatch,
    error_client,
) -> None:
    class MissingContentAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

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
                    "object": "chat.completion",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                            }
                        }
                    ],
                },
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        MissingContentAsyncClient,
    )

    response = error_client.post(
        "/chat",
        json={"conversation_id": "test-001", "message": "你好"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "LLM returned an invalid response.",
    }


def test_generate_reply_returns_none_and_logs_unavailable_when_usage_is_missing(
    monkeypatch,
    caplog,
) -> None:
    observed = {}

    class SuccessfulAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            observed["model"] = json["model"]

            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "模拟模型回答",
                            }
                        }
                    ],
                },
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        SuccessfulAsyncClient,
    )

    with caplog.at_level(logging.INFO, logger="app.services.llm"):
        result = asyncio.run(
            generate_reply(message="你好")
        )

    log_message = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.services.llm"
    ]

    assert result.answer == "模拟模型回答"
    assert result.prompt_tokens is None
    assert result.completion_tokens is None
    assert result.total_tokens is None
    assert len(log_message) == 1
    assert f"model={observed['model']}" in log_message[0]
    assert "status=200" in log_message[0]
    assert "latency_ms=" in log_message[0]
    assert "prompt_tokens=unavailable" in log_message[0]
    assert "completion_tokens=unavailable" in log_message[0]
    assert "total_tokens=unavailable" in log_message[0]


def test_chat_logs_token_usage_for_successful_llm_call(
    monkeypatch,
    caplog,
    client,
) -> None:
    class SuccessfulAsyncClient:
        def __init__(self, *, timeout=None) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback) -> None:
            return None

        async def post(self, url, *, headers, json):
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "模拟模型回答",
                            }
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 8,
                        "completion_tokens": 4,
                        "total_tokens": 12,
                    },
                },
            )

    monkeypatch.setattr(
        "app.services.llm.httpx.AsyncClient",
        SuccessfulAsyncClient,
    )

    with caplog.at_level(logging.INFO, logger="app.services.llm"):
        response = client.post(
            "/chat",
            json={"conversation_id": "test-001", "message": "你好"},
        )

    log_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.services.llm"
    ]

    assert response.status_code == 200
    assert response.json()["answer"] == "模拟模型回答"
    assert len(log_messages) == 1
    assert "prompt_tokens=8" in log_messages[0]
    assert "completion_tokens=4" in log_messages[0]
    assert "total_tokens=12" in log_messages[0]
