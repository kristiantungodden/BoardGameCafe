"""Application service for publishing reservation status transition domain events."""

from shared.domain.events import (
    ReservationCancelled,
    ReservationCompleted,
    ReservationSeated,
)


def _to_iso(ts):
    return ts.isoformat() if hasattr(ts, "isoformat") else ts


def _table_numbers_from_reservation(reservation):
    table_ids = getattr(reservation, "table_ids", None)
    if table_ids is not None:
        return list(table_ids)

    table_id = getattr(reservation, "table_id", None)
    return [table_id] if table_id is not None else []


def publish_reservation_transition_event(
    *,
    event_bus,
    reservation,
    actor_user_id=None,
    actor_role=None,
):
    """Publish a domain event for supported reservation transition statuses.

    Keeps transition-event policy in application layer rather than duplicating it
    across presentation routes.
    """
    if event_bus is None or reservation is None:
        return

    status = getattr(reservation, "status", None)
    if status not in {"cancelled", "seated", "completed"}:
        return

    role = actor_role or "unknown"
    table_numbers = _table_numbers_from_reservation(reservation)

    common = {
        "reservation_id": reservation.id,
        "user_id": reservation.customer_id,
        "table_numbers": table_numbers,
        "start_ts": _to_iso(reservation.start_ts),
        "end_ts": _to_iso(reservation.end_ts),
        "party_size": reservation.party_size,
    }

    if status == "cancelled":
        event_bus.publish(
            ReservationCancelled(
                **common,
                cancelled_by_user_id=actor_user_id,
                cancelled_by_role=role,
            )
        )
        return

    if status == "seated":
        event_bus.publish(
            ReservationSeated(
                **common,
                seated_by_user_id=actor_user_id,
                seated_by_role=role,
            )
        )
        return

    event_bus.publish(
        ReservationCompleted(
            **common,
            completed_by_user_id=actor_user_id,
            completed_by_role=role,
        )
    )
