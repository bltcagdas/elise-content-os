from fastapi.testclient import TestClient

from app.main import app


def test_telegram_webhook_without_secret_is_rejected():
    client = TestClient(app)
    response = client.post("/telegram/webhook", json={"callback_query": {"id": "1", "data": "published:plan"}})
    assert response.status_code == 401
