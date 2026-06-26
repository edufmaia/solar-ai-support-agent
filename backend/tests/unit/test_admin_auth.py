from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.main import create_app

client = TestClient(create_app())


@pytest.fixture
def admin_password(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "s3cret")
    get_settings.cache_clear()
    yield "s3cret"
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    get_settings.cache_clear()


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


def test_login_ok_returns_token(admin_password):
    res = _login("s3cret")
    assert res.status_code == 200
    token = res.json()["token"]
    assert isinstance(token, str) and len(token) >= 16


def test_logout_requires_token():
    res = client.post("/admin/logout")
    assert res.status_code == 401


def test_login_then_logout_succeeds(admin_password):
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
