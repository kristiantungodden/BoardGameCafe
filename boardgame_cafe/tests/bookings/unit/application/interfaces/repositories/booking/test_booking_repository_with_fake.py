from datetime import datetime

from features.bookings.domain.models.booking import Booking
from tests.bookings.unit.application.interfaces.repositories.booking.test_booking_repository_contract import (
    BookingRepositoryContract,
)


class FakeBookingRepository:
    def __init__(self):
        self._bookings = {}
        self._next_id = 1

    def save(self, booking: Booking) -> Booking:
        booking.id = self._next_id
        self._next_id += 1
        self._bookings[booking.id] = booking
        return booking

    def update(self, booking: Booking) -> Booking:
        self._bookings[booking.id] = booking
        return booking

    def get_by_id(self, booking_id: int):
        return self._bookings.get(booking_id)

    def delete(self, booking_id: int) -> None:
        if booking_id in self._bookings:
            del self._bookings[booking_id]

    def list_by_customer(self, customer_id: int):
        return sorted(
            [b for b in self._bookings.values() if b.customer_id == customer_id],
            key=lambda b: b.start_ts,
        )

    def find_overlapping_bookings(self, customer_id: int, start_ts: datetime, end_ts: datetime, statuses: set[str]):
        result = []
        for booking in self._bookings.values():
            if (
                booking.customer_id == customer_id
                and booking.start_ts < end_ts
                and booking.end_ts > start_ts
                and booking.status in statuses
            ):
                result.append(booking)
        return result


class TestBookingRepositoryWithFakeImpl(BookingRepositoryContract):
    def get_repository(self):
        return FakeBookingRepository()
