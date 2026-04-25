"""Register synchronous realtime event handlers for steward-facing updates."""

from shared.domain.events import (
    ReservationCancelled,
    ReservationCompleted,
    ReservationPaymentCompleted,
    ReservationSeated,
    ReservationUpdated,
)
from shared.domain.events import IncidentReported, IncidentDeleted
from shared.infrastructure.message_bus import realtime as realtime_bus


def publish_realtime_event(payload: dict, channel: str | None = None) -> None:
    """Publish a realtime payload through the infrastructure adapter."""
    if channel is None:
        return realtime_bus.publish_realtime_event(payload)
    return realtime_bus.publish_realtime_event(payload, channel=channel)


def _safe_publish(payload: dict, channel: str | None = None) -> None:
    try:
        # delegate to the module-level publish function so tests can monkeypatch
        if channel is None:
            publish_realtime_event(payload)
        else:
            publish_realtime_event(payload, channel=channel)
    except Exception as e:
        print(f"Error in event handler for {payload.get('event_type', '')}: {e}")


def _publish_reservation_payment_completed(event: ReservationPaymentCompleted) -> None:
    _safe_publish(
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
    _safe_publish(
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


def _publish_reservation_seated(event: ReservationSeated) -> None:
    _safe_publish(
        {
            "event_type": "reservation.seated",
            "data": {
                "reservation_id": event.reservation_id,
                "user_id": event.user_id,
                "table_numbers": list(event.table_numbers or []),
                "start_ts": event.start_ts,
                "end_ts": event.end_ts,
                "party_size": event.party_size,
                "seated_by_user_id": event.seated_by_user_id,
                "seated_by_role": event.seated_by_role,
            },
        }
    )


def _publish_reservation_completed(event: ReservationCompleted) -> None:
    _safe_publish(
        {
            "event_type": "reservation.completed",
            "data": {
                "reservation_id": event.reservation_id,
                "user_id": event.user_id,
                "table_numbers": list(event.table_numbers or []),
                "start_ts": event.start_ts,
                "end_ts": event.end_ts,
                "party_size": event.party_size,
                "completed_by_user_id": event.completed_by_user_id,
                "completed_by_role": event.completed_by_role,
            },
        }
    )


def _publish_reservation_updated(event: ReservationUpdated) -> None:
    _safe_publish(
        {
            "event_type": "reservation.updated",
            "data": {
                "reservation_id": event.reservation_id,
                "user_id": event.user_id,
                "table_numbers": list(event.table_numbers or []),
                "start_ts": event.start_ts,
                "end_ts": event.end_ts,
                "party_size": event.party_size,
                "updated_by_user_id": event.updated_by_user_id,
                "updated_by_role": event.updated_by_role,
                "notes": event.notes,
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
    event_bus.subscribe(ReservationSeated, _publish_reservation_seated)
    event_bus.subscribe(ReservationCompleted, _publish_reservation_completed)
    event_bus.subscribe(ReservationUpdated, _publish_reservation_updated)
    # Incident events
    def _publish_incident_reported(event: IncidentReported) -> None:
        _safe_publish(
            {
                "event_type": "incident.created",
                "data": {
                    "id": event.incident_id,
                    "game_copy_id": event.game_copy_id,
                    "reported_by": event.reported_by,
                    "incident_type": event.incident_type,
                    "note": event.note,
                    "created_at": event.created_at,
                },
            }
        )

    def _publish_incident_deleted(event: IncidentDeleted) -> None:
        _safe_publish({"event_type": "incident.deleted", "data": {"id": event.incident_id}})

    event_bus.subscribe(IncidentReported, _publish_incident_reported)
    event_bus.subscribe(IncidentDeleted, _publish_incident_deleted)
