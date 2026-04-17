"""Integration tests for the message bus system."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask

from shared.domain.events import UserRegistered, ReservationCreated
from shared.infrastructure.email.event_bus import EventBus
from shared.infrastructure.message_bus.celery_app import celery


@pytest.fixture
def fake_celery():
    """Provide a fake Celery instance for testing."""
    class FakeCelery:
        def __init__(self):
            self.calls = []

        def send_task(self, task_name, kwargs, retry=False):
            self.calls.append({"task_name": task_name, "kwargs": kwargs, "retry": retry})
            return None

    return FakeCelery()


class TestEndToEndEventFlow:
    """Test complete event flow from publication to task dispatch."""

    def test_user_registration_event_triggers_email_and_realtime_tasks(
        self, monkeypatch, fake_celery
    ):
        """
        When a UserRegistered event is published with both email and realtime
        subscriptions, both tasks should be dispatched to Celery.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()

        # Register handlers like in email_event_handler.py
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")
        event_bus.subscribe_task(UserRegistered, "shared.tasks.publish_realtime_event")

        # Publish event like from auth_routes.py
        event = UserRegistered(user_id=123, email="newuser@example.com")
        event_bus.publish(event)

        # Verify both tasks were dispatched
        assert len(fake_celery.calls) == 2
        
        task_names = [call["task_name"] for call in fake_celery.calls]
        assert "shared.tasks.send_welcome_email" in task_names
        assert "shared.tasks.publish_realtime_event" in task_names

        # Verify payloads are consistent
        for call in fake_celery.calls:
            payload = call["kwargs"]["event_payload"]
            assert payload["event_type"] == "UserRegistered"
            assert payload["data"]["user_id"] == 123
            assert payload["data"]["email"] == "newuser@example.com"

    def test_reservation_created_event_triggers_email_and_realtime_tasks(
        self, monkeypatch, fake_celery
    ):
        """
        When a ReservationCreated event is published with email and realtime
        subscriptions, both tasks should be dispatched.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()

        # Register handlers
        event_bus.subscribe_task(
            ReservationCreated, "shared.tasks.send_reservation_confirmation_email"
        )
        event_bus.subscribe_task(ReservationCreated, "shared.tasks.publish_realtime_event")

        # Publish event like from reservation_routes.py
        event = ReservationCreated(
            reservation_id=456,
            user_id=123,
            user_email="user@example.com",
            table_numbers=[4],
            start_ts="2026-04-17T19:00:00",
            end_ts="2026-04-17T21:00:00",
            party_size=4,
        )
        event_bus.publish(event)

        # Verify both tasks dispatched
        assert len(fake_celery.calls) == 2

        # Verify email task payload
        email_call = [c for c in fake_celery.calls
                      if c["task_name"] == "shared.tasks.send_reservation_confirmation_email"][0]
        email_payload = email_call["kwargs"]["event_payload"]
        assert email_payload["data"]["user_email"] == "user@example.com"
        assert email_payload["data"]["table_numbers"] == [4]
        assert email_payload["data"]["start_ts"] == "2026-04-17T19:00:00"
        assert email_payload["data"]["end_ts"] == "2026-04-17T21:00:00"
        assert email_payload["data"]["party_size"] == 4

        # Verify realtime task payload
        realtime_call = [c for c in fake_celery.calls
                         if c["task_name"] == "shared.tasks.publish_realtime_event"][0]
        realtime_payload = realtime_call["kwargs"]["event_payload"]
        assert realtime_payload["event_type"] == "ReservationCreated"

    def test_event_bus_can_handle_mixed_sync_handlers_and_async_tasks(
        self, monkeypatch, fake_celery
    ):
        """
        Event bus should support both sync handlers (for tests) and async tasks
        (for production) simultaneously.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        sync_handler_calls = []

        # Register both sync handler and async task
        event_bus.subscribe(UserRegistered, lambda e: sync_handler_calls.append(e))
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")

        # Publish event
        event = UserRegistered(user_id=123, email="test@example.com")
        event_bus.publish(event)

        # Both should execute
        assert len(sync_handler_calls) == 1
        assert len(fake_celery.calls) == 1

    def test_multiple_subscribers_receive_same_event(
        self, monkeypatch, fake_celery
    ):
        """
        When multiple handlers subscribe to the same event type, all should
        receive the event.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        sync_calls = ["email", "logging", "notification"]
        handlers = {
            "email": [],
            "logging": [],
            "notification": []
        }

        # Register multiple subscribers
        event_bus.subscribe(UserRegistered, lambda e: handlers["email"].append(e))
        event_bus.subscribe(UserRegistered, lambda e: handlers["logging"].append(e))
        event_bus.subscribe(UserRegistered, lambda e: handlers["notification"].append(e))
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")
        event_bus.subscribe_task(UserRegistered, "shared.tasks.publish_realtime_event")

        # Publish single event
        event = UserRegistered(user_id=123, email="test@example.com")
        event_bus.publish(event)

        # All handlers receive the event
        assert len(handlers["email"]) == 1
        assert len(handlers["logging"]) == 1
        assert len(handlers["notification"]) == 1
        assert len(fake_celery.calls) == 2  # Both tasks


class TestEventBusWithDifferentEventTypes:
    """Test event bus behavior with multiple different event types."""

    def test_different_event_types_routed_to_correct_handlers(
        self, monkeypatch, fake_celery
    ):
        """
        Different event types should be routed to their respective handlers
        only, not to unrelated handlers.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        user_handler_calls = []
        reservation_handler_calls = []

        # Register type-specific handlers
        event_bus.subscribe(UserRegistered, lambda e: user_handler_calls.append(e))
        event_bus.subscribe(ReservationCreated, lambda e: reservation_handler_calls.append(e))

        # Register type-specific tasks
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")
        event_bus.subscribe_task(
            ReservationCreated, "shared.tasks.send_reservation_confirmation_email"
        )

        # Publish different events
        event_bus.publish(UserRegistered(user_id=1, email="user1@example.com"))
        event_bus.publish(ReservationCreated(
            reservation_id=1, user_id=1, user_email="user1@example.com",
            table_numbers=[1], start_ts="2026-04-17T18:00:00", end_ts="2026-04-17T20:00:00", party_size=2
        ))
        event_bus.publish(UserRegistered(user_id=2, email="user2@example.com"))

        # Verify correct routing
        assert len(user_handler_calls) == 2
        assert len(reservation_handler_calls) == 1

        # Verify correct tasks
        email_tasks = [c for c in fake_celery.calls
                       if c["task_name"] == "shared.tasks.send_welcome_email"]
        assert len(email_tasks) == 2

        reservation_tasks = [c for c in fake_celery.calls
                             if c["task_name"] == "shared.tasks.send_reservation_confirmation_email"]
        assert len(reservation_tasks) == 1


class TestEventPayloadConsistency:
    """Test that event payloads are consistent across dispatch."""

    def test_same_payload_sent_to_all_subscribers(
        self, monkeypatch, fake_celery
    ):
        """
        All subscribers for an event should receive the same serialized payload.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "task1")
        event_bus.subscribe_task(UserRegistered, "task2")
        event_bus.subscribe_task(UserRegistered, "task3")

        event = UserRegistered(user_id=123, email="test@example.com")
        event_bus.publish(event)

        # Extract payloads
        payloads = [call["kwargs"]["event_payload"] for call in fake_celery.calls]

        # All should be identical
        assert len(payloads) == 3
        for i in range(1, len(payloads)):
            assert payloads[i] == payloads[0]

    def test_event_serialization_is_deterministic(
        self, monkeypatch, fake_celery
    ):
        """
        Publishing the same event twice should produce identical payloads.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "task")

        # Publish twice
        event_bus.publish(UserRegistered(user_id=123, email="test@example.com"))
        event_bus.publish(UserRegistered(user_id=123, email="test@example.com"))

        # Both payloads should be identical
        payload1 = fake_celery.calls[0]["kwargs"]["event_payload"]
        payload2 = fake_celery.calls[1]["kwargs"]["event_payload"]

        assert payload1 == payload2


class TestEventBusReliability:
    """Test event bus reliability under various conditions."""

    def test_single_failing_handler_does_not_prevent_other_handlers(
        self, monkeypatch, fake_celery, capsys
    ):
        """
        If one handler fails, other handlers and all tasks should still run.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        good_handler_calls = []

        def bad_handler(event):
            raise RuntimeError("Handler failed intentionally")

        event_bus.subscribe(UserRegistered, bad_handler)
        event_bus.subscribe(UserRegistered, lambda e: good_handler_calls.append(e))
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")
        event_bus.subscribe_task(UserRegistered, "shared.tasks.publish_realtime_event")

        event = UserRegistered(user_id=123, email="test@example.com")
        event_bus.publish(event)

        # Good handler and all tasks should still run
        assert len(good_handler_calls) == 1
        assert len(fake_celery.calls) == 2

        # Error should be logged
        captured = capsys.readouterr()
        assert "Error in event handler" in captured.out

    def test_single_failing_task_dispatch_does_not_prevent_other_tasks(
        self, monkeypatch, capsys
    ):
        """
        If one task dispatch fails, other task dispatches should still run.
        """
        class PartialFailCelery:
            def __init__(self):
                self.calls = []
                self.call_count = 0

            def send_task(self, task_name, kwargs, retry=False):
                self.call_count += 1
                if self.call_count == 1:
                    raise RuntimeError("First task dispatch failed")
                self.calls.append({"task_name": task_name, "kwargs": kwargs})

        fake_celery = PartialFailCelery()
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "task1")  # This will fail
        event_bus.subscribe_task(UserRegistered, "task2")  # This should still run

        event = UserRegistered(user_id=123, email="test@example.com")
        event_bus.publish(event)

        # Second task should have been dispatched despite first failure
        assert len(fake_celery.calls) == 1
        assert fake_celery.calls[0]["task_name"] == "task2"

        # Error should be logged
        captured = capsys.readouterr()
        assert "Error publishing event" in captured.out

    def test_event_bus_handles_rapid_publishing(
        self, monkeypatch, fake_celery
    ):
        """
        Event bus should handle rapid publication of events correctly.
        """
        monkeypatch.setattr(
            "shared.infrastructure.email.event_bus.celery", fake_celery
        )

        event_bus = EventBus()
        event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")

        # Rapidly publish multiple events
        for i in range(100):
            event_bus.publish(UserRegistered(user_id=i, email=f"user{i}@example.com"))

        # All should be dispatched
        assert len(fake_celery.calls) == 100

        # Verify data integrity of a few events
        assert fake_celery.calls[0]["kwargs"]["event_payload"]["data"]["user_id"] == 0
        assert fake_celery.calls[50]["kwargs"]["event_payload"]["data"]["user_id"] == 50
        assert fake_celery.calls[99]["kwargs"]["event_payload"]["data"]["user_id"] == 99
