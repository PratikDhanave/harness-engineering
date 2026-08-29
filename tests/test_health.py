from fastapi.testclient import TestClient

from harness.app import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_stub_echoes_and_passes_guardrail():
    r = client.post("/chat", json={"message": "hello"})
    assert r.status_code == 200
    body = r.json()
    assert "hello" in body["reply"]
    assert body["guardrail"] == "passed"


def test_chat_blocks_empty_input():
    r = client.post("/chat", json={"message": "   "})
    assert r.status_code == 200
    assert r.json()["guardrail"] == "empty input"
