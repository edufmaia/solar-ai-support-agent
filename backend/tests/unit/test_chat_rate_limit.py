import pytest
import redis
from app.config.database import get_db_session
from app.config.settings import get_settings
from app.main import create_app
from app.security.rate_limit import enforce_chat_rate_limit
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request


def make_request(ip="1.2.3.4", xff=None):
    headers = []
    if xff is not None:
        headers.append((b"x-forwarded-for", xff.encode()))
    scope = {"type": "http", "client": (ip, 12345), "headers": headers}
    return Request(scope)


class FakeRedis:
    """In-memory stand-in supporting the commands the limiter uses."""

    def __init__(self):
        self.store = {}
        self.expires = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, seconds):
        self.expires[key] = seconds
        return True

    def ttl(self, key):
        return self.expires.get(key, -1)


class BrokenRedis(FakeRedis):
    def incr(self, key):
        raise redis.exceptions.RedisError("down")


@pytest.fixture
def limits(monkeypatch):
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_MINUTE", "3")
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_DAY", "1000")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("CHAT_RATE_LIMIT_PER_MINUTE", raising=False)
    monkeypatch.delenv("CHAT_RATE_LIMIT_PER_DAY", raising=False)
    get_settings.cache_clear()


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("app.security.rate_limit.get_redis_client", lambda: fake)
    return fake


def test_allows_requests_up_to_the_limit(limits, fake_redis):
    for _ in range(3):
        enforce_chat_rate_limit(make_request())  # must not raise


def test_blocks_when_over_the_limit_with_retry_after(limits, fake_redis):
    for _ in range(3):
        enforce_chat_rate_limit(make_request())
    with pytest.raises(HTTPException) as exc:
        enforce_chat_rate_limit(make_request())
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"]


def test_counters_are_independent_per_ip(limits, fake_redis):
    for _ in range(3):
        enforce_chat_rate_limit(make_request(ip="1.1.1.1"))
    # a different client is unaffected
    enforce_chat_rate_limit(make_request(ip="2.2.2.2"))


def test_uses_x_forwarded_for_when_present(limits, fake_redis):
    for _ in range(3):
        enforce_chat_rate_limit(make_request(ip="10.0.0.1", xff="9.9.9.9"))
    # same proxy IP but a different forwarded client is a separate bucket
    enforce_chat_rate_limit(make_request(ip="10.0.0.1", xff="8.8.8.8"))
    # the throttled forwarded client stays blocked
    with pytest.raises(HTTPException):
        enforce_chat_rate_limit(make_request(ip="10.0.0.1", xff="9.9.9.9"))


def test_fails_open_when_redis_is_unavailable(limits, monkeypatch):
    monkeypatch.setattr("app.security.rate_limit.get_redis_client", lambda: BrokenRedis())
    for _ in range(20):
        enforce_chat_rate_limit(make_request())  # never raises


def test_zero_limit_disables_throttling(monkeypatch, fake_redis):
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_DAY", "0")
    get_settings.cache_clear()
    try:
        for _ in range(50):
            enforce_chat_rate_limit(make_request())
    finally:
        monkeypatch.delenv("CHAT_RATE_LIMIT_PER_MINUTE", raising=False)
        monkeypatch.delenv("CHAT_RATE_LIMIT_PER_DAY", raising=False)
        get_settings.cache_clear()


def test_chat_endpoint_returns_429_when_throttled(limits, fake_redis):
    # pre-fill the per-minute bucket to the limit so the next call trips it
    fake_redis.store["ratelimit:chat:min:5.5.5.5"] = 3
    app = create_app()
    app.dependency_overrides[get_db_session] = lambda: iter([None])
    client = TestClient(app)
    res = client.post("/chat", json={"message": "oi"}, headers={"X-Forwarded-For": "5.5.5.5"})
    assert res.status_code == 429
    assert res.headers.get("Retry-After")
