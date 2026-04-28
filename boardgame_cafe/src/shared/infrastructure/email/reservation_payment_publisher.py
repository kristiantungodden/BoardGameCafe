from __future__ import annotations

from flask import current_app

from features.bookings.infrastructure.repositories.booking_repository import SqlAlchemyBookingRepository
from features.reservations.infrastructure.repositories.table_reservation_repository import SqlAlchemyTableReservationRepository
from features.users.infrastructure.repositories.user_repository import SqlAlchemyUserRepository
from shared.application.services.reservation_payment_event_service import (
    publish_reservation_payment_completed_event,
)
from shared.infrastructure import db


def publish_reservation_payment_completed(booking_id: int) -> None:
    """Infrastructure adapter: wires concrete repos and delegates to the application service."""
    event_bus = getattr(current_app, "event_bus", None)
    if event_bus is None or not booking_id:
        return

    publish_reservation_payment_completed_event(
        booking_id,
        booking_repo=SqlAlchemyBookingRepository(session=db.session),
        user_repo=SqlAlchemyUserRepository(),
        table_reservation_repo=SqlAlchemyTableReservationRepository(session=db.session),
        event_bus=event_bus,
    )
