"""Infrastructure implementation of RealtimePublisherPort using Redis/SSE."""
from __future__ import annotations

from shared.application.interface.realtime_publisher_port import RealtimePublisherPort


class RedisRealtimePublisher(RealtimePublisherPort):
    """Publishes realtime events through the Redis-backed SSE channel."""

    def publish(self, payload: dict, channel: str | None = None) -> None:
        from shared.infrastructure.message_bus.realtime import publish_realtime_event

        if channel is None:
            publish_realtime_event(payload)
        else:
            publish_realtime_event(payload, channel=channel)
