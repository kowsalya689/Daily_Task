"""Run from the project root:  pytest -q
Uses your real trained model. Telegram is mocked, so no messages are sent."""
import pytest
from fastapi.testclient import TestClient

from src.api import app as app_module
from src.alerts import telegram_alert

POSITIVE = "This product is amazing, works perfectly and arrived early. Love it!"
NEGATIVE = "Terrible quality. It arrived broken, the seller never replied and I want a refund."


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    app_module._hits.clear()
    sent = []

    def fake_post(url, json=None, timeout=None):
        sent.append((url, json))

        class Resp:
            def raise_for_status(self):
                pass
        return Resp()

    monkeypatch.setattr(telegram_alert.requests, "post", fake_post)
    c = TestClient(app_module.app)
    c.sent = sent
    return c


def test_page_loads(client):
    assert "Tell us how we did" in client.get("/").text


def test_positive_sends_no_alert(client):
    r = client.post("/predict", json={"text": POSITIVE})
    assert r.status_code == 200 and r.json()["sentiment"] == "positive"
    assert r.json()["owner_alerted"] is False and client.sent == []


def test_negative_alerts_owner(client):
    r = client.post("/predict", json={"text": NEGATIVE, "contact": "Ravi 98400 00000"})
    body = r.json()
    assert body["sentiment"] == "negative" and body["owner_alerted"] is True
    (url, payload), = client.sent
    assert url.endswith("/sendMessage") and payload["chat_id"] == "12345"
    assert NEGATIVE in payload["text"] and "Ravi" in payload["text"]


def test_negative_without_telegram_still_responds(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    r = client.post("/predict", json={"text": NEGATIVE})
    assert r.status_code == 200 and r.json()["owner_alerted"] is False


def test_rejects_empty_and_symbol_only_text(client):
    assert client.post("/predict", json={"text": "  "}).status_code == 422
    assert client.post("/predict", json={"text": "!!! ???"}).status_code == 422


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(app_module, "RATE_LIMIT", 2)
    codes = [client.post("/predict", json={"text": POSITIVE}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
