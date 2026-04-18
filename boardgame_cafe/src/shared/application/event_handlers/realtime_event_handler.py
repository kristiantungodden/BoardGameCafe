"""Register synchronous realtime event handlers for steward-facing updates."""

from shared.domain.events import ReservationCancelled, ReservationPaymentCompleted
from shared.infrastructure.message_bus.realtime import publish_realtime_event


def _publish_reservation_payment_completed(event: ReservationPaymentCompleted) -> None:
    publish_realtime_event(
        {
            "event_type": "reservation.payment.completed",
            "data": {
                "reservation_id": event.reservation_id,
                "user_id": event.user_id,
                "user_email": event.user_email,
                "table_numbers": list(event.table_numbers or []),
                "start_ts": event.start_ts,
                "end_ts": event.end_ts,
                "party_size": event.party_size,
            },
        }
    )


def _publish_reservation_cancelled(event: ReservationCancelled) -> None:
    publish_realtime_event(
        {
            "event_type": "reservation.cancelled",
            "data": {
                "reservation_id": event.reservation_id,
                "user_id": event.user_id,
                "table_numbers": list(event.table_numbers or []),
                "start_ts": event.start_ts,
                "end_ts": event.end_ts,
                "party_size": event.party_size,
                "cancelled_by_user_id": event.cancelled_by_user_id,
                "cancelled_by_role": event.cancelled_by_role,
            },
        }
    )


def register_realtime_event_handlers(event_bus) -> None:
    """Wire domain events to realtime pub/sub payloads."""

    event_bus.subscribe(
        ReservationPaymentCompleted,
        _publish_reservation_payment_completed,
    )
    event_bus.subscribe(ReservationCancelled, _publish_reservation_cancelled)
