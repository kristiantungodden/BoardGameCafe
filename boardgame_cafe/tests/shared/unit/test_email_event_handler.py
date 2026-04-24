"""Tests for email event handler registration and task subscriptions."""
import pytest
from unittest.mock import Mock, patch

from shared.domain.events import (
    ReservationPaymentCompleted,
    UserRegistered,
)
from shared.infrastructure.email.event_bus import EventBus


class FakeCelery:
    """Mock Celery for tracking task dispatch."""
    def __init__(self):
        self.calls = []

    def send_task(self, task_name, kwargs, retry=False):
        self.calls.append({"task_name": task_name, "kwargs": kwargs, "retry": retry})
        return None


class TestEmailEventHandlerRegistration:
    """Test email event handler registration and task subscriptions."""

    def test_register_user_registered_task_subscription(self, monkeypatch):
        """UserRegistered events should be mapped to send_welcome_email task."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()

        # Register subscription (as done in email_event_handler.py)
        event_bus.subscribe_task(
            UserRegistered, "shared.tasks.send_welcome_email"
        )

        # Publish event
        event = UserRegistered(user_id=123, email="newuser@example.com")
        event_bus.publish(event)

        # Verify task dispatched
        assert len(fake_celery.calls) == 1
        call = fake_celery.calls[0]
        assert call["task_name"] == "shared.tasks.send_welcome_email"
        
        # Verify payload structure
        payload = call["kwargs"]["event_payload"]
        assert payload["event_type"] == "UserRegistered"
        assert payload["data"]["user_id"] == 123
        assert payload["data"]["email"] == "newuser@example.com"

    def test_register_reservation_payment_completed_task_subscription(self, monkeypatch):
        """ReservationPaymentCompleted events should map to send_reservation_confirmation_email."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()

        # Register subscription
        event_bus.subscribe_task(
            ReservationPaymentCompleted, "shared.tasks.send_reservation_confirmation_email"
        )

        # Publish event
        event = ReservationPaymentCompleted(
            reservation_id=456,
            user_id=123,
            user_email="user@example.com",
            table_numbers=[2],
            start_ts="2026-04-17T17:00:00",
            end_ts="2026-04-17T19:00:00",
            party_size=4,
        )
        event_bus.publish(event)

        # Verify task dispatched
        assert len(fake_celery.calls) == 1
        call = fake_celery.calls[0]
        assert call["task_name"] == "shared.tasks.send_reservation_confirmation_email"
        
        # Verify payload structure
        payload = call["kwargs"]["event_payload"]
        assert payload["event_type"] == "ReservationPaymentCompleted"
        assert payload["data"]["reservation_id"] == 456
        assert payload["data"]["user_id"] == 123
        assert payload["data"]["user_email"] == "user@example.com"
        assert payload["data"]["table_numbers"] == [2]
        assert payload["data"]["start_ts"] == "2026-04-17T17:00:00"
        assert payload["data"]["end_ts"] == "2026-04-17T19:00:00"
        assert payload["data"]["party_size"] == 4

    def test_register_realtime_event_task_subscription(self, monkeypatch):
        """Events should also trigger realtime event publishing task."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()

        # Register multiple subscriptions for same event
        event_bus.subscribe_task(
            UserRegistered, "shared.tasks.send_welcome_email"
        )
        event_bus.subscribe_task(
            UserRegistered, "shared.tasks.publish_realtime_event"
        )

        # Publish event
        event = UserRegistered(user_id=123, email="newuser@example.com")
        event_bus.publish(event)

        # Verify both tasks dispatched
        assert len(fake_celery.calls) == 2
        task_names = [call["task_name"] for call in fake_celery.calls]
        assert "shared.tasks.send_welcome_email" in task_names
        assert "shared.tasks.publish_realtime_event" in task_names

    def test_multiple_event_types_with_same_handler_instance(self, monkeypatch):
        """Event bus should support subscriptions for multiple event types."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()

        # Subscribe both events to realtime publishing (actual wiring)
        event_bus.subscribe_task(UserRegistered, "shared.tasks.publish_realtime_event")
        event_bus.subscribe_task(ReservationPaymentCompleted, "shared.tasks.publish_realtime_event")

        # Publish both events
        event_bus.publish(UserRegistered(user_id=1, email="user@example.com"))
        event_bus.publish(ReservationPaymentCompleted(
            reservation_id=1, user_id=1, user_email="user@example.com",
            table_numbers=[1], start_ts="2026-04-17T18:00:00", end_ts="2026-04-17T20:00:00", party_size=2
        ))

        # Verify both generated task calls
        assert len(fake_celery.calls) == 2
        for call in fake_celery.calls:
            assert call["task_name"] == "shared.tasks.publish_realtime_event"

    def test_event_handler_payload_excludes_module_info(self):
        """Event handler should only receive event payload, not internal metadata."""
        event_bus = EventBus()
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(UserRegistered, handler)
        event = UserRegistered(user_id=123, email="test@example.com")
        event_bus.publish(event)

        # Handler receives actual event object, not serialized payload
        assert len(received_events) == 1
        assert isinstance(received_events[0], UserRegistered)
        assert received_events[0].user_id == 123


class TestEventPayloadStructure:
    """Test the structure of event payloads sent to Celery tasks."""

    def test_payload_has_required_fields(self, monkeypatch):
        """Event payload should include event_type, event_module, and data."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")

        event = UserRegistered(user_id=123, email="test@example.com")
        event_bus.publish(event)

        payload = fake_celery.calls[0]["kwargs"]["event_payload"]
        assert "event_type" in payload
        assert "event_module" in payload
        assert "data" in payload

    def test_event_type_is_class_name(self, monkeypatch):
        """event_type should be the event class name."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "task")
        event_bus.publish(UserRegistered(user_id=1, email="test@example.com"))

        payload = fake_celery.calls[0]["kwargs"]["event_payload"]
        assert payload["event_type"] == "UserRegistered"

    def test_event_module_contains_module_path(self, monkeypatch):
        """event_module should contain the module path of the event class."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "task")
        event_bus.publish(UserRegistered(user_id=1, email="test@example.com"))

        payload = fake_celery.calls[0]["kwargs"]["event_payload"]
        # Module name uses snake_case, not class name
        assert "shared.domain.events" in payload["event_module"]
        assert "user_registered" in payload["event_module"]

    def test_data_contains_all_event_fields(self, monkeypatch):
        """data should contain all event fields serialized properly."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(ReservationPaymentCompleted, "task")

        event = ReservationPaymentCompleted(
            reservation_id=456,
            user_id=123,
            user_email="user@example.com",
            table_numbers=[3],
            start_ts="2026-04-18T15:00:00",
            end_ts="2026-04-18T17:00:00",
            party_size=5,
        )
        event_bus.publish(event)

        data = fake_celery.calls[0]["kwargs"]["event_payload"]["data"]
        assert data["reservation_id"] == 456
        assert data["user_id"] == 123
        assert data["user_email"] == "user@example.com"
        assert data["table_numbers"] == [3]
        assert data["start_ts"] == "2026-04-18T15:00:00"
        assert data["end_ts"] == "2026-04-18T17:00:00"
        assert data["party_size"] == 5

    def test_payload_is_json_serializable(self, monkeypatch):
        """Event payload should be JSON serializable."""
        import json
        
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "task")
        event_bus.publish(UserRegistered(user_id=1, email="test@example.com"))

        payload = fake_celery.calls[0]["kwargs"]["event_payload"]
        
        # Should not raise
        json_str = json.dumps(payload)
        restored = json.loads(json_str)
        
        assert restored["event_type"] == "UserRegistered"
        assert restored["data"]["user_id"] == 1
        assert restored["data"]["email"] == "test@example.com"
