"""Tests for realtime domain-event handler registration."""

from shared.domain.events import (
    ReservationCancelled,
    ReservationCompleted,
    ReservationCreated,
    ReservationPaymentCompleted,
    ReservationSeated,
)
from shared.infrastructure.email.event_bus import EventBus
from shared.application.event_handlers.realtime_event_handler import (
    register_realtime_event_handlers,
)


def _sample_reservation_payment_completed_event() -> ReservationPaymentCompleted:
    return ReservationPaymentCompleted(
        reservation_id=99,
        user_id=12,
        user_email="guest@example.com",
        table_numbers=[1, 4],
        start_ts="2026-04-18T17:00:00",
        end_ts="2026-04-18T19:00:00",
        party_size=5,
    )


def _sample_reservation_cancelled_event() -> ReservationCancelled:
    return ReservationCancelled(
        reservation_id=77,
        user_id=12,
        table_numbers=[1, 4],
        start_ts="2026-04-18T17:00:00",
        end_ts="2026-04-18T19:00:00",
        party_size=5,
        cancelled_by_user_id=12,
        cancelled_by_role="customer",
    )


def _sample_reservation_seated_event() -> ReservationSeated:
    return ReservationSeated(
        reservation_id=88,
        user_id=12,
        table_numbers=[2, 3],
        start_ts="2026-04-18T17:00:00",
        end_ts="2026-04-18T19:00:00",
        party_size=4,
        seated_by_user_id=9,
        seated_by_role="staff",
    )


def _sample_reservation_completed_event() -> ReservationCompleted:
    return ReservationCompleted(
        reservation_id=66,
        user_id=12,
        table_numbers=[3],
        start_ts="2026-04-18T17:00:00",
        end_ts="2026-04-18T19:00:00",
        party_size=2,
        completed_by_user_id=9,
        completed_by_role="staff",
    )


def test_register_realtime_event_handlers_publishes_canonical_reservation_payment_completed(
    monkeypatch,
):
    published_payloads = []

    def fake_publish_realtime_event(payload):
        published_payloads.append(payload)

    monkeypatch.setattr(
        "shared.application.event_handlers.realtime_event_handler.publish_realtime_event",
        fake_publish_realtime_event,
    )

    event_bus = EventBus()
    register_realtime_event_handlers(event_bus)

    event_bus.publish(_sample_reservation_payment_completed_event())

    assert len(published_payloads) == 1
    payload = published_payloads[0]
    assert payload["event_type"] == "reservation.payment.completed"
    assert payload["data"]["reservation_id"] == 99
    assert payload["data"]["user_email"] == "guest@example.com"
    assert payload["data"]["table_numbers"] == [1, 4]


def test_register_realtime_event_handlers_is_best_effort(monkeypatch):
    def failing_publish(_payload):
        raise RuntimeError("redis is unavailable")

    monkeypatch.setattr(
        "shared.application.event_handlers.realtime_event_handler.publish_realtime_event",
        failing_publish,
    )

    event_bus = EventBus()
    register_realtime_event_handlers(event_bus)

    # EventBus should not raise even if realtime publishing fails.
    event_bus.publish(_sample_reservation_payment_completed_event())


def test_register_realtime_event_handlers_does_not_publish_on_reservation_created(
    monkeypatch,
):
    published_payloads = []

    def fake_publish_realtime_event(payload):
        published_payloads.append(payload)

    monkeypatch.setattr(
        "shared.application.event_handlers.realtime_event_handler.publish_realtime_event",
        fake_publish_realtime_event,
    )

    event_bus = EventBus()
    register_realtime_event_handlers(event_bus)

    event_bus.publish(
        ReservationCreated(
            reservation_id=101,
            user_id=12,
            user_email="guest@example.com",
            table_numbers=[2],
            start_ts="2026-04-18T17:00:00",
            end_ts="2026-04-18T19:00:00",
            party_size=2,
        )
    )

    assert published_payloads == []


def test_register_realtime_event_handlers_publishes_reservation_cancelled(monkeypatch):
    published_payloads = []

    def fake_publish_realtime_event(payload):
        published_payloads.append(payload)

    monkeypatch.setattr(
        "shared.application.event_handlers.realtime_event_handler.publish_realtime_event",
        fake_publish_realtime_event,
    )

    event_bus = EventBus()
    register_realtime_event_handlers(event_bus)

    event_bus.publish(_sample_reservation_cancelled_event())

    assert len(published_payloads) == 1
    payload = published_payloads[0]
    assert payload["event_type"] == "reservation.cancelled"
    assert payload["data"]["reservation_id"] == 77
    assert payload["data"]["cancelled_by_role"] == "customer"


def test_register_realtime_event_handlers_publishes_reservation_seated(monkeypatch):
    published_payloads = []

    def fake_publish_realtime_event(payload):
        published_payloads.append(payload)

    monkeypatch.setattr(
        "shared.application.event_handlers.realtime_event_handler.publish_realtime_event",
        fake_publish_realtime_event,
    )

    event_bus = EventBus()
    register_realtime_event_handlers(event_bus)

    event_bus.publish(_sample_reservation_seated_event())

    assert len(published_payloads) == 1
    payload = published_payloads[0]
    assert payload["event_type"] == "reservation.seated"
    assert payload["data"]["reservation_id"] == 88
    assert payload["data"]["seated_by_role"] == "staff"


def test_register_realtime_event_handlers_publishes_reservation_completed(monkeypatch):
    published_payloads = []

    def fake_publish_realtime_event(payload):
        published_payloads.append(payload)

    monkeypatch.setattr(
        "shared.application.event_handlers.realtime_event_handler.publish_realtime_event",
        fake_publish_realtime_event,
    )

    event_bus = EventBus()
    register_realtime_event_handlers(event_bus)

    event_bus.publish(_sample_reservation_completed_event())

    assert len(published_payloads) == 1
    payload = published_payloads[0]
    assert payload["event_type"] == "reservation.completed"
    assert payload["data"]["reservation_id"] == 66
    assert payload["data"]["completed_by_role"] == "staff"
