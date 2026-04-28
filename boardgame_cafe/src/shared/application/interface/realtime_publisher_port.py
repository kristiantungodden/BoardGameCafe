"""Abstract port for publishing realtime events.

The application layer depends on this interface; the infrastructure layer
provides a concrete implementation (e.g. Redis/SSE via RedisRealtimePublisher).
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class RealtimePublisherPort(ABC):
    """Port for publishing realtime payloads to connected clients."""

    @abstractmethod
    def publish(self, payload: dict, channel: str | None = None) -> None:
        """Publish *payload* to the given channel (or the default channel)."""
