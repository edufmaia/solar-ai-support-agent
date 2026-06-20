from functools import lru_cache

import redis

from .settings import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    """Module-level Redis client. Lazy — does not connect until first command."""
    settings = get_settings()
    return redis.Redis.from_url(settings.get_redis_url(), decode_responses=True)
