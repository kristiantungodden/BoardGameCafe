"""Comprehensive tests for EventBus sync handlers, task subscriptions, and serialization."""
import pytest
from datetime import datetime, date
from enum import Enum

from shared.domain.events import UserRegistered, ReservationCreated
from shared.infrastructure.email.event_bus import EventBus


class BookingStatus(Enum):
    """Example enum for testing enum serialization."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class FakeCelery:
    """Mock Celery for tracking task dispatch."""
    def __init__(self):
        self.calls = []

    def send_task(self, task_name, kwargs, retry=False):
        self.calls.append({"task_name": task_name, "kwargs": kwargs, "retry": retry})
        return None


class TestEventBusSyncHandlers:
    """Test EventBus synchronous handler subscription and invocation."""

    def test_subscribe_and_call_sync_handler(self):
        """Handler should be called when event is published."""
        event_bus = EventBus()
        handler_calls = []

        def test_handler(event):
            handler_calls.append(event)

        event_bus.subscribe(UserRegistered, test_handler)
        event = UserRegistered(user_id=1, email="test@example.com")
        event_bus.publish(event)

        assert len(handler_calls) == 1
        assert handler_calls[0].user_id == 1
        assert handler_calls[0].email == "test@example.com"

    def test_multiple_handlers_for_same_event(self):
        """Multiple handlers should all be called for same event type."""
        event_bus = EventBus()
        calls = {"handler1": [], "handler2": []}

        event_bus.subscribe(UserRegistered, lambda e: calls["handler1"].append(e))
        event_bus.subscribe(UserRegistered, lambda e: calls["handler2"].append(e))

        event = UserRegistered(user_id=1, email="test@example.com")
        event_bus.publish(event)

        assert len(calls["handler1"]) == 1
        assert len(calls["handler2"]) == 1

    def test_handlers_isolated_by_event_type(self):
        """Handler for EventA should not be called for EventB."""
        event_bus = EventBus()
        user_calls = []
        reservation_calls = []

        event_bus.subscribe(UserRegistered, lambda e: user_calls.append(e))
        event_bus.subscribe(ReservationCreated, lambda e: reservation_calls.append(e))

        event_bus.publish(UserRegistered(user_id=1, email="test@example.com"))
        event_bus.publish(ReservationCreated(
            reservation_id=1, user_id=1, user_email="test@example.com",
            table_numbers=[2], start_ts="2026-04-17T17:00:00", end_ts="2026-04-17T19:00:00", party_size=4
        ))

        assert len(user_calls) == 1
        assert len(reservation_calls) == 1

    def test_handler_exception_does_not_break_other_handlers(self, capsys):
        """If one handler raises, others should still be called."""
        event_bus = EventBus()
        good_calls = []

        def bad_handler(event):
            raise ValueError("Handler failed")

        def good_handler(event):
            good_calls.append(event)

        event_bus.subscribe(UserRegistered, bad_handler)
        event_bus.subscribe(UserRegistered, good_handler)

        event = UserRegistered(user_id=1, email="test@example.com")
        event_bus.publish(event)  # Should not raise

        assert len(good_calls) == 1
        captured = capsys.readouterr()
        assert "Error in event handler" in captured.out


class TestEventBusTaskSubscriptions:
    """Test EventBus async task subscriptions."""

    def test_subscribe_task_dispatches_to_celery(self, monkeypatch):
        """Published event should trigger Celery task dispatch."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")

        event = UserRegistered(user_id=1, email="test@example.com")
        event_bus.publish(event)

        assert len(fake_celery.calls) == 1
        call = fake_celery.calls[0]
        assert call["task_name"] == "shared.tasks.send_welcome_email"
        assert call["retry"] is False

    def test_task_payload_contains_event_type_and_module(self, monkeypatch):
        """Task payload should include event_type and event_module."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")
        event_bus.publish(UserRegistered(user_id=1, email="test@example.com"))

        payload = fake_celery.calls[0]["kwargs"]["event_payload"]
        assert payload["event_type"] == "UserRegistered"
        assert "user_registered" in payload["event_module"]  # module is snake_case

    def test_multiple_task_subscriptions_for_same_event(self, monkeypatch):
        """Event should dispatch to all subscribed tasks."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "task1")
        event_bus.subscribe_task(UserRegistered, "task2")

        event = UserRegistered(user_id=1, email="test@example.com")
        event_bus.publish(event)

        assert len(fake_celery.calls) == 2
        task_names = [call["task_name"] for call in fake_celery.calls]
        assert "task1" in task_names
        assert "task2" in task_names

    def test_task_dispatch_exception_logged_not_raised(self, monkeypatch, capsys):
        """Task dispatch error should be logged, not crash publish()."""
        def bad_send_task(task_name, kwargs, retry=False):
            raise RuntimeError("Broker unavailable")

        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery.send_task",
            bad_send_task
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")

        event = UserRegistered(user_id=1, email="test@example.com")
        event_bus.publish(event)  # Should not raise

        captured = capsys.readouterr()
        assert "Error publishing event" in captured.out
        assert "Broker unavailable" in captured.out


class TestEventSerialization:
    """Test EventBus event serialization for JSON compatibility."""

    def test_serialize_simple_event(self):
        """Simple event with primitive fields should serialize correctly."""
        event_bus = EventBus()
        event = UserRegistered(user_id=1, email="test@example.com")
        serialized = event_bus._serialize_event(event)

        assert serialized["user_id"] == 1
        assert serialized["email"] == "test@example.com"

    def test_serialize_datetime_field(self):
        """Datetime fields should serialize to ISO format."""
        event_bus = EventBus()

        class TimestampedEvent:
            def __init__(self, created_at):
                self.created_at = created_at

        now = datetime(2026, 4, 15, 10, 30, 45)
        event = TimestampedEvent(created_at=now)
        serialized = event_bus._serialize_event(event)

        assert serialized["created_at"] == "2026-04-15T10:30:45"

    def test_serialize_date_field(self):
        """Date fields should serialize to ISO format."""
        event_bus = EventBus()

        class DateEvent:
            def __init__(self, start_date):
                self.start_date = start_date

        d = date(2026, 4, 15)
        event = DateEvent(start_date=d)
        serialized = event_bus._serialize_event(event)

        assert serialized["start_date"] == "2026-04-15"

    def test_serialize_enum_field(self):
        """Enum fields should be serialized to their value."""
        event_bus = EventBus()

        class EnumEvent:
            def __init__(self, status):
                self.status = status

        event = EnumEvent(status=BookingStatus.CONFIRMED)
        serialized = event_bus._serialize_event(event)

        assert serialized["status"] == "confirmed"

    def test_serialize_nested_dict(self):
        """Nested dictionaries should be recursively serialized."""
        event_bus = EventBus()

        class NestedEvent:
            def __init__(self, metadata):
                self.metadata = metadata

        event = NestedEvent(metadata={"key": "value", "count": 42})
        serialized = event_bus._serialize_event(event)

        assert serialized["metadata"]["key"] == "value"
        assert serialized["metadata"]["count"] == 42

    def test_serialize_list_field(self):
        """List fields should be recursively serialized."""
        event_bus = EventBus()

        class ListEvent:
            def __init__(self, items):
                self.items = items

        event = ListEvent(items=["a", "b", 42, None])
        serialized = event_bus._serialize_event(event)

        assert serialized["items"] == ["a", "b", 42, None]

    def test_serialize_list_with_datetime(self):
        """Lists containing datetime should be serialized correctly."""
        event_bus = EventBus()

        class ListDateEvent:
            def __init__(self, timestamps):
                self.timestamps = timestamps

        now = datetime(2026, 4, 15, 10, 30, 45)
        event = ListDateEvent(timestamps=[now])
        serialized = event_bus._serialize_event(event)

        assert serialized["timestamps"][0] == "2026-04-15T10:30:45"

    def test_serialize_list_with_enums(self):
        """Lists containing enums should be serialized correctly."""
        event_bus = EventBus()

        class ListEnumEvent:
            def __init__(self, statuses):
                self.statuses = statuses

        event = ListEnumEvent(statuses=[BookingStatus.CONFIRMED, BookingStatus.PENDING])
        serialized = event_bus._serialize_event(event)

        assert serialized["statuses"] == ["confirmed", "pending"]

    def test_serialize_complex_nested_structure(self):
        """Complex nested structures should serialize completely."""
        event_bus = EventBus()

        class ComplexEvent:
            def __init__(self, data):
                self.data = data

        event = ComplexEvent(data={
            "timestamp": datetime(2026, 4, 15, 10, 30, 45),
            "status": BookingStatus.CONFIRMED,
            "items": ["a", 1, None],
            "nested": {"key": "value"}
        })
        serialized = event_bus._serialize_event(event)

        assert serialized["data"]["timestamp"] == "2026-04-15T10:30:45"
        assert serialized["data"]["status"] == "confirmed"
        assert serialized["data"]["items"] == ["a", 1, None]
        assert serialized["data"]["nested"]["key"] == "value"

    def test_serialize_none_values(self):
        """None values should remain as None."""
        event_bus = EventBus()

        class NoneEvent:
            def __init__(self, optional_field):
                self.optional_field = optional_field

        event = NoneEvent(optional_field=None)
        serialized = event_bus._serialize_event(event)

        assert serialized["optional_field"] is None

    def test_serialize_unknown_types_as_string(self):
        """Unknown types should be converted to string."""
        event_bus = EventBus()

        class CustomObj:
            def __str__(self):
                return "custom_object"

        class CustomTypeEvent:
            def __init__(self, obj):
                self.obj = obj

        event = CustomTypeEvent(obj=CustomObj())
        serialized = event_bus._serialize_event(event)

        assert serialized["obj"] == "custom_object"


class TestEventBusBothSyncAndAsync:
    """Test EventBus with both sync handlers and async tasks."""

    def test_both_handlers_and_tasks_dispatched(self, monkeypatch):
        """Event should dispatch to both sync handlers and async tasks."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        handler_calls = []

        event_bus.subscribe(UserRegistered, lambda e: handler_calls.append(e))
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")

        event = UserRegistered(user_id=1, email="test@example.com")
        event_bus.publish(event)

        assert len(handler_calls) == 1
        assert len(fake_celery.calls) == 1

    def test_handler_and_task_exception_both_handled(self, monkeypatch, capsys):
        """Handler exception should not prevent task dispatch."""
        fake_celery = FakeCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()

        def bad_handler(event):
            raise ValueError("Handler failed")

        event_bus.subscribe(UserRegistered, bad_handler)
        event_bus.subscribe_task(UserRegistered, "task1")

        event = UserRegistered(user_id=1, email="test@example.com")
        event_bus.publish(event)

        # Both the handler error and successful task dispatch should occur
        assert len(fake_celery.calls) == 1
        captured = capsys.readouterr()
        assert "Error in event handler" in captured.out
