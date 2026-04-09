from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Sequence

from features.bookings.application.interfaces.booking_repository_interface import (
    BookingRepositoryInterface,
)
from features.bookings.domain.models.booking import Booking
from features.reservations.application.interfaces.table_reservation_repository_interface import (
    TableReservationRepositoryInterface,
)
from features.reservations.domain.models.table_reservation import TableReservation
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES
from shared.domain.exceptions import ValidationError

_OPENING_TIME = time(hour=9, minute=0)
_CLOSING_TIME = time(hour=23, minute=0)


@dataclass
class BookingCommand:
    customer_id: int
    table_id: int | None
    start_ts: datetime
    end_ts: datetime
    party_size: int
    notes: Optional[str] = None


class CreateBookingRecordUseCase:
    def __init__(
        self,
        booking_repo: BookingRepositoryInterface,
        table_reservation_repo: TableReservationRepositoryInterface,
    ):
        self.booking_repo = booking_repo
        self.table_reservation_repo = table_reservation_repo

    def execute(self, cmd: BookingCommand) -> Booking:
        if cmd.table_id is None:
            raise ValidationError("table_id must be selected before creating booking")

        if cmd.start_ts.date() != cmd.end_ts.date():
            raise ValidationError(
                "Reservations must start and end on the same day (no overnight bookings)."
            )

        if cmd.start_ts.time() < _OPENING_TIME or cmd.end_ts.time() > _CLOSING_TIME:
            raise ValidationError(
                "Reservations must be within opening hours: 09:00 to 23:00."
            )

        overlapping = self.booking_repo.find_overlapping_bookings(
            customer_id=cmd.customer_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
            statuses=OVERLAP_BLOCKING_STATUSES,
        )
        if overlapping:
            raise ValidationError(
                "Customer already has an active booking in the requested timeslot."
            )

        booking = Booking(
            customer_id=cmd.customer_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
            party_size=cmd.party_size,
            notes=cmd.notes,
        )
        booking = self.booking_repo.save(booking)

        self.table_reservation_repo.save(
            TableReservation(booking_id=booking.id, table_id=cmd.table_id)
        )

        return booking


class ListBookingsUseCase:
    def __init__(self, booking_repo: BookingRepositoryInterface):
        self.booking_repo = booking_repo

    def execute(self) -> Sequence[Booking]:
        return self.booking_repo.list_all()


class GetBookingByIdUseCase:
    def __init__(self, booking_repo: BookingRepositoryInterface):
        self.booking_repo = booking_repo

    def execute(self, booking_id: int) -> Optional[Booking]:
        return self.booking_repo.get_by_id(booking_id)


class CancelBookingUseCase:
    def __init__(self, booking_repo: BookingRepositoryInterface):
        self.booking_repo = booking_repo

    def execute(self, booking_id: int) -> Optional[Booking]:
        booking = self.booking_repo.get_by_id(booking_id)
        if booking is None:
            return None
        booking.cancel()
        return self.booking_repo.update(booking)


class SeatBookingUseCase:
    def __init__(self, booking_repo: BookingRepositoryInterface):
        self.booking_repo = booking_repo

    def execute(self, booking_id: int) -> Optional[Booking]:
        booking = self.booking_repo.get_by_id(booking_id)
        if booking is None:
            return None
        booking.seat()
        return self.booking_repo.update(booking)


class CompleteBookingUseCase:
    def __init__(self, booking_repo: BookingRepositoryInterface):
        self.booking_repo = booking_repo

    def execute(self, booking_id: int) -> Optional[Booking]:
        booking = self.booking_repo.get_by_id(booking_id)
        if booking is None:
            return None
        booking.complete()
        return self.booking_repo.update(booking)


class MarkBookingNoShowUseCase:
    def __init__(self, booking_repo: BookingRepositoryInterface):
        self.booking_repo = booking_repo

    def execute(self, booking_id: int) -> Optional[Booking]:
        booking = self.booking_repo.get_by_id(booking_id)
        if booking is None:
            return None
        booking.mark_no_show()
        return self.booking_repo.update(booking)
