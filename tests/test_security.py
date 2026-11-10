"""
HS AI SOLUTIONS - SECURITY & AUTHENTICATION TESTS
Founder: Harshan Seliyan
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.security import sanitize_input, RateLimiter

client = TestClient(app)


def test_missing_api_key():
    resp = client.get("/v1/models")
    assert resp.status_code == 401
    assert "Missing authentication credentials" in resp.json()["detail"]


def test_invalid_api_key():
    resp = client.get("/v1/models", headers={"Authorization": "Bearer invalid-key-xyz"})
    assert resp.status_code == 403
    assert "Invalid API key" in resp.json()["detail"]


def test_valid_api_key():
    resp = client.get("/v1/models", headers={"Authorization": f"Bearer {settings.API_KEY}"})
    assert resp.status_code == 200
    assert resp.json()["object"] == "list"


def test_valid_x_api_key_header():
    resp = client.get("/v1/models", headers={"X-API-Key": settings.API_KEY})
    assert resp.status_code == 200


def test_admin_endpoint_forbidden_with_normal_key():
    resp = client.post("/admin/model/unload", headers={"Authorization": f"Bearer {settings.API_KEY}"})
    # If API_KEY != ADMIN_KEY, should be 403
    if settings.API_KEY != settings.ADMIN_KEY:
        assert resp.status_code == 403
        assert "Administrative privileges required" in resp.json()["detail"]


def test_admin_endpoint_success_with_admin_key():
    resp = client.post("/admin/model/unload", headers={"Authorization": f"Bearer {settings.ADMIN_KEY}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_input_sanitizer():
    raw = "Hello\x00World!"
    cleaned = sanitize_input(raw)
    assert "\x00" not in cleaned
    assert cleaned == "HelloWorld!"


def test_rate_limiter():
    limiter = RateLimiter(requests_per_minute=3)
    ip = "192.168.1.50"
    assert limiter.is_allowed(ip)[0] is True
    assert limiter.is_allowed(ip)[0] is True
    assert limiter.is_allowed(ip)[0] is True
    allowed, retry_after = limiter.is_allowed(ip)
    assert allowed is False
    assert retry_after > 0
