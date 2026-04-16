from __future__ import annotations

import json

from cachelib.simple import SimpleCache
from flask import current_app
from redis import Redis
from redis.exceptions import RedisError

_CACHE_EXTENSION_KEY = "booking_draft_store"
_CACHE_KEY_PREFIX = "reservation_draft:user:"
_DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7


def init_booking_draft_store(app):
    """Initialize the ephemeral server-side store for booking progress."""
    ttl_seconds = app.config.get("BOOKING_DRAFT_TTL_SECONDS", _DEFAULT_TTL_SECONDS)
    redis_url = app.config.get("REDIS_URL")
    require_redis = bool(app.config.get("BOOKING_DRAFT_REDIS_REQUIRED", False))

    if app.config.get("TESTING") and not redis_url:
        # Keep tests self-contained when no Redis service is configured.
        store = SimpleCache(default_timeout=ttl_seconds)
        store.clear()
        app.extensions[_CACHE_EXTENSION_KEY] = store
        return store

    if not redis_url:
        if require_redis:
            raise RuntimeError("REDIS_URL is required for booking draft storage")

        store = SimpleCache(default_timeout=ttl_seconds)
        app.extensions[_CACHE_EXTENSION_KEY] = store
        app.logger.warning(
            "Booking draft storage: REDIS_URL not set, using in-memory fallback cache."
        )
        return store

    try:
        store = Redis.from_url(redis_url, decode_responses=True)
        store.ping()
        app.extensions[_CACHE_EXTENSION_KEY] = store
        return store
    except RedisError as exc:
        if require_redis:
            raise RuntimeError(f"Could not connect to Redis at {redis_url}") from exc

        store = SimpleCache(default_timeout=ttl_seconds)
        app.extensions[_CACHE_EXTENSION_KEY] = store
        app.logger.warning(
            "Booking draft storage: Redis unavailable at %s (%s). Using in-memory fallback cache.",
            redis_url,
            exc,
        )
        return store


def _get_booking_draft_store():
    store = current_app.extensions.get(_CACHE_EXTENSION_KEY)
    if store is None:
        raise RuntimeError("Booking draft store has not been initialized")
    return store


def _booking_draft_key(user_id: int) -> str:
    return f"{_CACHE_KEY_PREFIX}{int(user_id)}"


def get_booking_draft(user_id: int) -> dict:
    store = _get_booking_draft_store()
    key = _booking_draft_key(user_id)

    if isinstance(store, Redis):
        raw = store.get(key)
        if not raw:
            return {}
        try:
            draft = json.loads(raw)
            return draft if isinstance(draft, dict) else {}
        except json.JSONDecodeError:
            return {}

    draft = store.get(key)
    return draft if isinstance(draft, dict) else {}


def save_booking_draft(user_id: int, draft: dict) -> dict:
    store = _get_booking_draft_store()
    key = _booking_draft_key(user_id)
    ttl_seconds = current_app.config.get("BOOKING_DRAFT_TTL_SECONDS", _DEFAULT_TTL_SECONDS)

    if isinstance(store, Redis):
        store.setex(key, ttl_seconds, json.dumps(draft, separators=(",", ":")))
        return draft

    store.set(key, draft, timeout=ttl_seconds)
    return draft


def clear_booking_draft(user_id: int) -> None:
    store = _get_booking_draft_store()
    key = _booking_draft_key(user_id)

    if isinstance(store, Redis):
        store.delete(key)
        return

    store.delete(key)
