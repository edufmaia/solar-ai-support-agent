from uuid import uuid4

import pytest
from app.config.settings import get_settings
from app.main import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())


@pytest.fixture
def admin_password(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    get_settings.cache_clear()
    yield "s3cret"
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    get_settings.cache_clear()


class _FakeRedis:
    """In-memory stand-in so login/logout tests don't need a live Redis."""

    def __init__(self):
        self._store = {}

    def set(self, key, value, ex=None):
        self._store[key] = value
        return True

    def exists(self, key):
        return 1 if key in self._store else 0

    def delete(self, key):
        self._store.pop(key, None)
        return 1


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr("app.security.admin_auth.get_redis_client", lambda: fake)
    return fake


def _login(password):
    return client.post("/admin/login", json={"password": password})


def test_login_disabled_without_password(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    get_settings.cache_clear()
    res = _login("anything")
    assert res.status_code == 503


def test_login_wrong_password(admin_password):
    res = _login("wrong")
    assert res.status_code == 401


def test_login_ok_returns_token(admin_password, fake_redis):
    res = _login("s3cret")
    assert res.status_code == 200
    token = res.json()["token"]
    assert isinstance(token, str) and len(token) >= 16


def test_logout_requires_token():
    res = client.post("/admin/logout")
    assert res.status_code == 401


def test_login_then_logout_succeeds(admin_password, fake_redis):
    token = _login("s3cret").json()["token"]
    res = client.post("/admin/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204
    # token no longer valid
    again = client.post("/admin/logout", headers={"Authorization": f"Bearer {token}"})
    assert again.status_code == 401


def test_metrics_requires_admin():
    res = client.get("/metrics")
    assert res.status_code == 401


def test_conversation_detail_requires_admin():
    res = client.get(f"/conversations/{uuid4()}")
    assert res.status_code == 401


def test_admin_metrics_requires_token():
    assert client.get("/admin/metrics").status_code == 401


def test_admin_conversations_requires_token():
    assert client.get("/admin/conversations").status_code == 401


def test_admin_conversation_detail_requires_token():
    assert client.get(f"/admin/conversations/{uuid4()}").status_code == 401
