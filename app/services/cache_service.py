# pyrefly: ignore [missing-import]
import json
import logging
from typing import Any, Optional

import redis
from app.config import settings

logger = logging.getLogger("complaint_system.cache")

# ---------------------------------------------------------------------------
# Single shared Redis client. If REDIS_URL is unset or unreachable, all
# cache operations silently no-op instead of crashing the app — caching is
# a performance optimization, not a hard dependency.
# ---------------------------------------------------------------------------
_redis_client: Optional[redis.Redis] = None

if settings.REDIS_URL:
    try:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        _redis_client.ping()
        logger.info("Redis cache connected")
    except Exception as exc:
        logger.warning("Redis unavailable, caching disabled", extra={"error": str(exc)})
        _redis_client = None
else:
    logger.info("REDIS_URL not set, caching disabled")


def get_cached(key: str) -> Optional[Any]:
    """Returns the cached value for `key`, or None on miss / Redis unavailable."""
    if not _redis_client:
        return None
    try:
        raw = _redis_client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception as exc:
        logger.warning("Cache read failed", extra={"key": key, "error": str(exc)})
        return None


def set_cached(key: str, value: Any, ttl_seconds: int = 60) -> None:
    """Stores `value` under `key` with a TTL. Silently no-ops on failure."""
    if not _redis_client:
        return
    try:
        _redis_client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception as exc:
        logger.warning("Cache write failed", extra={"key": key, "error": str(exc)})


def invalidate_cached(key: str) -> None:
    """Deletes a cached key. Silently no-ops on failure."""
    if not _redis_client:
        return
    try:
        _redis_client.delete(key)
    except Exception as exc:
        logger.warning("Cache invalidate failed", extra={"key": key, "error": str(exc)})
