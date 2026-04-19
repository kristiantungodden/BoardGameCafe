from types import SimpleNamespace

from shared.application.services.reservation_transition_event_publisher import (
    publish_reservation_transition_event,
)
from shared.domain.events import (
    ReservationCancelled,
    ReservationCompleted,
    ReservationSeated,
)


class FakeEventBus:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def _reservation(status: str):
    return SimpleNamespace(
        id=10,
        customer_id=7,
        table_id=3,
        start_ts="2026-04-19T18:00:00",
        end_ts="2026-04-19T20:00:00",
        party_size=4,
        status=status,
    )


def test_publish_transition_event_ignores_unhandled_status():
    event_bus = FakeEventBus()

    publish_reservation_transition_event(
        event_bus=event_bus,
        reservation=_reservation("confirmed"),
        actor_user_id=99,
        actor_role="staff",
    )

    assert event_bus.events == []


def test_publish_transition_event_publishes_seated_with_actor_role():
    event_bus = FakeEventBus()

    publish_reservation_transition_event(
        event_bus=event_bus,
        reservation=_reservation("seated"),
        actor_user_id=99,
        actor_role="staff",
    )

    assert len(event_bus.events) == 1
    event = event_bus.events[0]
    assert isinstance(event, ReservationSeated)
    assert event.reservation_id == 10
    assert event.seated_by_user_id == 99
    assert event.seated_by_role == "staff"
    assert event.table_numbers == [3]


def test_publish_transition_event_publishes_completed_with_unknown_role_fallback():
    event_bus = FakeEventBus()

    publish_reservation_transition_event(
        event_bus=event_bus,
        reservation=_reservation("completed"),
        actor_user_id=None,
        actor_role=None,
    )

    assert len(event_bus.events) == 1
    event = event_bus.events[0]
    assert isinstance(event, ReservationCompleted)
    assert event.completed_by_role == "unknown"


def test_publish_transition_event_publishes_cancelled_with_table_ids_if_available():
    event_bus = FakeEventBus()
    reservation = _reservation("cancelled")
    reservation.table_ids = [1, 2]

    publish_reservation_transition_event(
        event_bus=event_bus,
        reservation=reservation,
        actor_user_id=55,
        actor_role="customer",
    )

    assert len(event_bus.events) == 1
    event = event_bus.events[0]
    assert isinstance(event, ReservationCancelled)
    assert event.table_numbers == [1, 2]
    assert event.cancelled_by_user_id == 55
    assert event.cancelled_by_role == "customer"
