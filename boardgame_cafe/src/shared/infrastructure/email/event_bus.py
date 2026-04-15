from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from shared.infrastructure.message_bus import celery


class EventBus:
    """Hybrid event bus: in-process handlers + Celery-backed task subscriptions."""

    def __init__(self):
        self._handlers: dict[type, list] = {}
        self._task_subscriptions: dict[type, list[str]] = {}

    def subscribe(self, event_type, handler):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_task(self, event_type, task_name: str):
        if event_type not in self._task_subscriptions:
            self._task_subscriptions[event_type] = []
        self._task_subscriptions[event_type].append(task_name)

    def publish(self, event):
        event_type = type(event)

        # Local handlers are useful in tests and for simple synchronous hooks.
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as exc:
                print(f"Error in event handler for {event_type.__name__}: {exc}")

        task_payload = {
            "event_type": event_type.__name__,
            "event_module": event_type.__module__,
            "data": self._serialize_event(event),
        }
        for task_name in self._task_subscriptions.get(event_type, []):
            try:
                celery.send_task(
                    task_name,
                    kwargs={"event_payload": task_payload},
                    retry=False,
                )
            except Exception as exc:
                print(
                    f"Error publishing event '{event_type.__name__}' to task '{task_name}': {exc}"
                )

    def _serialize_event(self, event) -> dict[str, Any]:
        if is_dataclass(event):
            raw = asdict(event)
        elif hasattr(event, "__dict__"):
            raw = vars(event)
        else:
            raw = {"value": str(event)}

        return {key: self._to_json_value(value) for key, value in raw.items()}

    def _to_json_value(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [self._to_json_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._to_json_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._to_json_value(item) for key, item in value.items()}
        return str(value)