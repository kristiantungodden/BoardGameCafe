from __future__ import annotations

from flask import current_app

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.users.infrastructure.database.user_db import UserDB
from shared.domain.events import ReservationPaymentCompleted
from shared.infrastructure import db


def publish_reservation_payment_completed(booking_id: int) -> None:
    event_bus = getattr(current_app, "event_bus", None)
    if event_bus is None or not booking_id:
        return

    booking = db.session.get(BookingDB, booking_id)
    if booking is None:
        return

    customer = db.session.get(UserDB, booking.customer_id)
    customer_email = getattr(customer, "email", None)
    if not customer_email:
        return

    table_numbers = []
    table_links = TableReservationDB.query.filter_by(booking_id=booking.id).all()
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
