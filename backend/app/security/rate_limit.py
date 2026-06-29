import redis
from fastapi import HTTPException, Request, status

from ..config.redis_client import get_redis_client
from ..config.settings import get_settings

_PREFIX = "ratelimit:chat"
_MINUTE_SECONDS = 60
_DAY_SECONDS = 86400
_DETAIL = "Muitas mensagens em pouco tempo. Aguarde um momento e tente novamente."


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _enforce_window(ip: str, label: str, window_seconds: int, limit: int) -> None:
    if limit <= 0:
        return  # window disabled
    key = f"{_PREFIX}:{label}:{ip}"
    client = get_redis_client()
    try:
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_seconds)
    except redis.exceptions.RedisError:
        return  # fail-open: never block the chat because of a cache outage
    if count > limit:
        try:
            ttl = client.ttl(key)
        except redis.exceptions.RedisError:
            ttl = window_seconds
        retry_after = ttl if isinstance(ttl, int) and ttl > 0 else window_seconds
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_DETAIL,
            headers={"Retry-After": str(retry_after)},
        )


def enforce_chat_rate_limit(request: Request) -> None:
    """FastAPI dependency: throttle ``/chat`` per client IP using Redis fixed
    windows (per-minute and per-day). Set either limit to ``0`` to disable it.

    Protects against runaway LLM cost/abuse from an open public endpoint. The IP
    is taken from ``X-Forwarded-For`` (first hop) when behind a reverse proxy,
    falling back to the socket peer.
    """
    settings = get_settings()
    ip = _client_ip(request)
    _enforce_window(ip, "min", _MINUTE_SECONDS, settings.chat_rate_limit_per_minute)
    _enforce_window(ip, "day", _DAY_SECONDS, settings.chat_rate_limit_per_day)
