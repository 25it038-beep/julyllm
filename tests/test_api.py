"""
HS AI SOLUTIONS - FASTAPI ENDPOINTS & CHAT TEST SUITE
Founder: Harshan Seliyan
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

# Force mock mode for integration tests
os.environ["MOCK_INFERENCE"] = "true"

from app.main import app
from app.config import settings
from app.model_loader import model_manager

client = TestClient(app)

AUTH_HEADERS = {
    "Authorization": f"Bearer {settings.API_KEY}",
    "X-API-Key": settings.API_KEY
}


@pytest.fixture(autouse=True)
def ensure_mock_loaded():
    """Ensure mock model is active during test execution."""
    model_manager.is_mock = True
    if not model_manager.is_loaded:
        model_manager.load()
    yield


def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "JULY Cloud AI"
    assert data["founder"] == "Harshan Seliyan"


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ready", "initializing")
    assert data["is_mock"] is True


def test_status_endpoint():
    resp = client.get("/v1/status", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["founder"] == "Harshan Seliyan"
    assert data["is_mock"] is True


def test_model_info_endpoint():
    resp = client.get("/v1/model/info", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert "JULY" in data["model_name"]
    assert data["founder"] == "Harshan Seliyan"


def test_native_chat_non_streaming():
    payload = {
        "message": "What is HS AI Solutions?",
        "max_tokens": 64,
        "stream": False
    }
    resp = client.post("/v1/chat", headers=AUTH_HEADERS, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "JULY" in data["response"]
    assert "conversation_id" in data
    assert data["is_mock"] is True


def test_native_chat_streaming():
    payload = {
        "message": "Give me a quick stream test.",
        "max_tokens": 64,
        "stream": True
    }
    with client.stream("POST", "/v1/chat", headers=AUTH_HEADERS, json=payload) as response:
        assert response.status_code == 200
        lines = [line for line in response.iter_lines() if line]
        assert any("data: " in line for line in lines)
        assert any("[DONE]" in line for line in lines)


def test_openai_chat_completions():
    payload = {
        "model": "july-3b",
        "messages": [
            {"role": "user", "content": "Hello July"}
        ],
        "max_tokens": 64,
        "stream": False
    }
    resp = client.post("/v1/chat/completions", headers=AUTH_HEADERS, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) > 0
    assert "JULY" in data["choices"][0]["message"]["content"]


def test_openai_completions():
    payload = {
        "prompt": "Say this is a test",
        "max_tokens": 32
    }
    resp = client.post("/v1/completions", headers=AUTH_HEADERS, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "text_completion"
    assert len(data["choices"]) > 0


def test_conversations_lifecycle():
    # 1. Send first message in a new session
    session_id = "test-session-12345"
    payload = {
        "message": "My secret code is HS-2026",
        "conversation_id": session_id,
        "stream": False
    }
    resp = client.post("/v1/chat", headers=AUTH_HEADERS, json=payload)
    assert resp.status_code == 200

    # 2. Retrieve history
    resp = client.get(f"/v1/conversations/{session_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) >= 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "My secret code is HS-2026"

    # 3. List conversations
    resp = client.get("/v1/conversations", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    conv_list = resp.json()
    assert any(c["conversation_id"] == session_id for c in conv_list)

    # 4. Delete session
    resp = client.delete(f"/v1/conversations/{session_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # 5. Confirm deletion
    resp = client.get(f"/v1/conversations/{session_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 404
