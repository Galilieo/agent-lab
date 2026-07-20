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
