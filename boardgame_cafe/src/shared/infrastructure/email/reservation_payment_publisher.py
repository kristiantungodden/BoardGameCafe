from __future__ import annotations

from flask import current_app

from features.bookings.infrastructure.repositories.booking_repository import SqlAlchemyBookingRepository
from features.reservations.infrastructure.repositories.table_reservation_repository import SqlAlchemyTableReservationRepository
from features.users.infrastructure.repositories.user_repository import SqlAlchemyUserRepository
from shared.domain.events import ReservationPaymentCompleted
from shared.infrastructure import db


def publish_reservation_payment_completed(booking_id: int) -> None:
    event_bus = getattr(current_app, "event_bus", None)
    if event_bus is None or not booking_id:
        return

    booking = SqlAlchemyBookingRepository(session=db.session).get_by_id(booking_id)
    if booking is None:
        return

    customer = SqlAlchemyUserRepository().get_by_id(booking.customer_id)
    customer_email = getattr(customer, "email", None)
    if not customer_email:
        return

    table_numbers = []
    table_links = SqlAlchemyTableReservationRepository(session=db.session).list_by_booking_id(booking.id)
    for link in table_links:
        table = getattr(link, "table", None)
        table_nr = getattr(table, "table_nr", None)
        table_numbers.append(table_nr if table_nr is not None else link.table_id)

    event_bus.publish(
        ReservationPaymentCompleted(
            reservation_id=booking.id,
            user_id=booking.customer_id,
            user_email=customer_email,
            table_numbers=table_numbers,
            start_ts=booking.start_ts.isoformat(),
            end_ts=booking.end_ts.isoformat(),
            party_size=booking.party_size,
        )
    )
