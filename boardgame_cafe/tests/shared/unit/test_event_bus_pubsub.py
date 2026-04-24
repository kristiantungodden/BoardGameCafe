"""Tests for EventBus task dispatch matching actual email_event_handler.py wiring."""
from shared.domain.events import ReservationPaymentCompleted, UserRegistered
from shared.infrastructure.email.event_bus import EventBus


class FakeCelery:
    def __init__(self):
        self.calls = []

    def send_task(self, task_name, kwargs, retry=False):
        self.calls.append((task_name, kwargs, retry))


def test_user_registered_dispatches_to_welcome_email(monkeypatch):
    """UserRegistered should dispatch to send_welcome_email task (actual wiring)."""
    fake_celery = FakeCelery()
    monkeypatch.setattr("shared.infrastructure.email.event_bus.celery", fake_celery)

    event_bus = EventBus()
    event_bus.subscribe_task(UserRegistered, "shared.tasks.send_welcome_email")

    event_bus.publish(UserRegistered(user_id=7, email="newuser@example.com"))

    assert len(fake_celery.calls) == 1
    task_name, kwargs, retry = fake_celery.calls[0]
    assert task_name == "shared.tasks.send_welcome_email"
    assert retry is False
    payload = kwargs["event_payload"]
    assert payload["event_type"] == "UserRegistered"
    assert payload["data"]["email"] == "newuser@example.com"


def test_reservation_payment_completed_dispatches_to_confirmation_email(monkeypatch):
    """ReservationPaymentCompleted should dispatch to send_reservation_confirmation_email task (actual wiring)."""
    fake_celery = FakeCelery()
    monkeypatch.setattr("shared.infrastructure.email.event_bus.celery", fake_celery)

    event_bus = EventBus()
    event_bus.subscribe_task(
        ReservationPaymentCompleted,
        "shared.tasks.send_reservation_confirmation_email",
    )

    event_bus.publish(
        ReservationPaymentCompleted(
            reservation_id=10,
            user_id=7,
            user_email="user@example.com",
            table_numbers=[2],
            start_ts="2026-04-17T17:00:00",
            end_ts="2026-04-17T19:00:00",
            party_size=4,
        )
    )

    assert len(fake_celery.calls) == 1
    task_name, kwargs, retry = fake_celery.calls[0]
    assert task_name == "shared.tasks.send_reservation_confirmation_email"
    assert retry is False
    payload = kwargs["event_payload"]
    assert payload["event_type"] == "ReservationPaymentCompleted"
    assert payload["data"]["user_email"] == "user@example.com"


def test_both_events_dispatch_to_publish_realtime_event(monkeypatch):
    """UserRegistered and ReservationPaymentCompleted both dispatch to publish_realtime_event (actual wiring)."""
    fake_celery = FakeCelery()
    monkeypatch.setattr("shared.infrastructure.email.event_bus.celery", fake_celery)

    event_bus = EventBus()
    event_bus.subscribe_task(UserRegistered, "shared.tasks.publish_realtime_event")
    event_bus.subscribe_task(ReservationPaymentCompleted, "shared.tasks.publish_realtime_event")

    event_bus.publish(UserRegistered(user_id=1, email="user@example.com"))
    event_bus.publish(
        ReservationPaymentCompleted(
            reservation_id=10,
            user_id=1,
            user_email="user@example.com",
            table_numbers=[2],
            start_ts="2026-04-17T17:00:00",
            end_ts="2026-04-17T19:00:00",
            party_size=4,
        )
    )

    assert len(fake_celery.calls) == 2
    for task_name, kwargs, retry in fake_celery.calls:
        assert task_name == "shared.tasks.publish_realtime_event"
