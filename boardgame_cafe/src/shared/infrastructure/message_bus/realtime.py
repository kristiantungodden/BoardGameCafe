from __future__ import annotations

import json
from typing import Generator

from flask import current_app

try:
    import redis
except ImportError:  # pragma: no cover - runtime environment dependent
    redis = None


def get_redis_client(url: str | None = None) -> redis.Redis:
    if redis is None:
        raise RuntimeError(
            "Redis client not installed. Install dependency 'redis' to enable realtime pub/sub."
        )

    redis_url = url or current_app.config["REDIS_URL"]
    return redis.Redis.from_url(redis_url, decode_responses=True)


def publish_realtime_event(payload: dict, channel: str | None = None) -> None:
    redis_client = get_redis_client()
    target_channel = channel or current_app.config["REALTIME_EVENTS_CHANNEL"]
    redis_client.publish(target_channel, json.dumps(payload, default=str))


def stream_realtime_events(channel: str | None = None) -> Generator[str, None, None]:
    redis_client = get_redis_client()
    target_channel = channel or current_app.config["REALTIME_EVENTS_CHANNEL"]
    pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(target_channel)

    # Warmup event helps clients know the stream is connected.
    yield "event: ready\ndata: {\"status\":\"connected\"}\n\n"

    try:
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            yield f"event: domain_event\ndata: {data}\n\n"
    finally:
        pubsub.close()
