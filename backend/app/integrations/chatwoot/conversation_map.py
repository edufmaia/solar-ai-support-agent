from uuid import UUID

import redis

from ...config.redis_client import get_redis_client
from ...config.settings import get_settings


class ChatwootConversationMap:
    """Maps a Chatwoot conversation to our internal conversation UUID via Redis.

    Best-effort: Redis errors degrade to "no mapping" (a new conversation is
    created) rather than failing the webhook.
    """

    KEY_PREFIX = "chatwoot:"

    def __init__(self, client: redis.Redis, ttl_seconds: int) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    def _key(self, account_id: int, cw_conversation_id: int) -> str:
        return f"{self.KEY_PREFIX}{account_id}:{cw_conversation_id}"

    def get(self, account_id: int, cw_conversation_id: int) -> UUID | None:
        try:
            raw = self.client.get(self._key(account_id, cw_conversation_id))
        except redis.exceptions.RedisError:
            return None
        if raw is None:
            return None
        try:
            return UUID(raw)
        except (ValueError, AttributeError):
            return None

    def set(self, account_id: int, cw_conversation_id: int, conversation_id: UUID) -> None:
        try:
            self.client.set(
                self._key(account_id, cw_conversation_id),
                str(conversation_id),
                ex=self.ttl_seconds,
            )
        except redis.exceptions.RedisError:
            return


def build_chatwoot_conversation_map() -> ChatwootConversationMap:
    settings = get_settings()
    return ChatwootConversationMap(
        get_redis_client(), settings.chatwoot_conversation_ttl_seconds
    )
