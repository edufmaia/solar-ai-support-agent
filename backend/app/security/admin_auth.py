import secrets

import redis
from fastapi import Header, HTTPException, status

from ..config.redis_client import get_redis_client
from ..config.settings import get_settings

SESSION_PREFIX = "admin_session:"


def login(password: str) -> str:
    settings = get_settings()
    configured = settings.admin_password
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="admin login not configured",
        )
    if not secrets.compare_digest(password, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    token = secrets.token_urlsafe(32)
    try:
        get_redis_client().set(
            f"{SESSION_PREFIX}{token}", "1", ex=settings.admin_session_ttl_seconds
        )
    except redis.exceptions.RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="session store unavailable",
        ) from exc
    return token


def logout(token: str) -> None:
    try:
        get_redis_client().delete(f"{SESSION_PREFIX}{token}")
    except redis.exceptions.RedisError:
        pass  # best-effort; the session expires on its own anyway


def _token_from_header(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing admin token",
        )
    return authorization[len("Bearer ") :].strip()


def require_admin(authorization: str | None = Header(default=None)) -> None:
    token = _token_from_header(authorization)
    try:
        exists = get_redis_client().exists(f"{SESSION_PREFIX}{token}")
    except redis.exceptions.RedisError as exc:
        # fail-closed: never open on infra failure
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="session store unavailable",
        ) from exc
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid admin token",
        )
