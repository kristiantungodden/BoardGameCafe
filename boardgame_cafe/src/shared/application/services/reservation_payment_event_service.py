"""Application service for publishing the ReservationPaymentCompleted domain event.

This service lives in the application layer. It fetches the booking, customer,
and table data through repository interfaces and publishes the event to the
event bus. The composition layer wires in concrete repository implementations.
"""
from __future__ import annotations

from features.bookings.application.interfaces.booking_repository_interface import (
    BookingRepositoryInterface,
)
from features.reservations.application.interfaces.table_reservation_repository_interface import (
    TableReservationRepositoryInterface,
)
from features.users.application.interfaces import UserRepositoryInterface
from shared.domain.events import ReservationPaymentCompleted


def publish_reservation_payment_completed_event(
    booking_id: int,
    *,
    booking_repo: BookingRepositoryInterface,
    user_repo: UserRepositoryInterface,
    table_reservation_repo: TableReservationRepositoryInterface,
    event_bus,
) -> None:
    """Build and publish a ReservationPaymentCompleted event.

    Fetches booking, customer and table data through repository interfaces,
    then publishes the domain event to the provided event bus.
    """
    if not booking_id:
        return

    booking = booking_repo.get_by_id(booking_id)
    if booking is None:
        return

    customer = user_repo.get_by_id(booking.customer_id)
    customer_email = getattr(customer, "email", None)
    if not customer_email:
        return

    table_numbers = []
    table_links = table_reservation_repo.list_by_booking_id(booking.id)
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
