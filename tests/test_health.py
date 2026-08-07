from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_typed_placeholder_response() -> None:
    response = client.post(
        "/chat",
        json={"conversation_id": "test-001", "message": "你好"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_id": "test-001",
        "answer": "Chat model is not connected yet.",
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
