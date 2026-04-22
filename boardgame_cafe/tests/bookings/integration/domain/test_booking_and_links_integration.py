from datetime import datetime, timezone

from features.bookings.domain.models.booking import Booking
from features.reservations.domain.models.reservation_game import ReservationGame
from features.reservations.domain.models.table_reservation import TableReservation


def test_booking_links_to_table_and_game_entities():
    booking = Booking(
        customer_id=1,
        start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
        end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
        party_size=4,
        id=1,
    )

    table_link = TableReservation(booking_id=booking.id, table_id=5)
    game_link = ReservationGame(booking_id=booking.id, requested_game_id=10, game_copy_id=42)

    assert table_link.booking_id == booking.id
    assert game_link.booking_id == booking.id


def test_booking_status_lifecycle_is_aggregate_owned():
    booking = Booking(
        customer_id=1,
        start_ts=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
        end_ts=datetime(2026, 4, 10, 20, 0, tzinfo=timezone.utc),
        party_size=4,
    )

    booking.confirm()
    booking.seat()
    booking.complete()

    assert booking.status == "completed"
