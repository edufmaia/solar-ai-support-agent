from uuid import UUID

import redis

from ..config.redis_client import get_redis_client
from ..config.settings import get_settings
from ..schemas.session import SessionState


class SessionStoreError(Exception):
    """Raised when the session store (Redis) cannot be reached."""


class RedisSessionStore:
    KEY_PREFIX = "session:"

    def __init__(self, client: redis.Redis, ttl_seconds: int) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    def _key(self, conversation_id: UUID) -> str:
        return f"{self.KEY_PREFIX}{conversation_id}"

    def get(self, conversation_id: UUID) -> SessionState | None:
        try:
            raw = self.client.get(self._key(conversation_id))
        except redis.exceptions.RedisError as exc:
            raise SessionStoreError(str(exc)) from exc

        if raw is None:
            return None
        return SessionState.model_validate_json(raw)

    def save(self, state: SessionState) -> None:
        try:
            self.client.set(
                self._key(state.conversation_id),
                state.model_dump_json(),
                ex=self.ttl_seconds,
            )
        except redis.exceptions.RedisError as exc:
            raise SessionStoreError(str(exc)) from exc


def build_session_store() -> RedisSessionStore:
    settings = get_settings()
    return RedisSessionStore(get_redis_client(), settings.session_ttl_seconds)
