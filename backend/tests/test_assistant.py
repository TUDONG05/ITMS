from fastapi.testclient import TestClient

from app.main import app


def test_assistant_chat_requires_authentication() -> None:
    response = TestClient(app).post(
        "/api/v1/assistant/chat",
        json={"message": "Task gần nhất của tôi là gì?"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MISSING_ACCESS_TOKEN"
