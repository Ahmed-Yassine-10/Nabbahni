"""Redis cache helper with graceful degradation when Redis is unavailable."""
from __future__ import annotations

import json
from typing import Any

import redis

from app.core.config import settings

try:
    _client: redis.Redis | None = redis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=1
    )
    _client.ping()
except Exception:  # Redis optional in dev — fall back to no-op cache
    _client = None


def cache_get(key: str) -> Any | None:
    if _client is None:
        return None
    try:
        raw = _client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    if _client is None:
        return
    try:
        _client.set(key, json.dumps(value, default=str), ex=ttl or settings.cache_ttl_seconds)
    except Exception:
        pass


def cache_invalidate(pattern: str) -> None:
    if _client is None:
        return
    try:
        for key in _client.scan_iter(match=pattern):
            _client.delete(key)
    except Exception:
        pass
