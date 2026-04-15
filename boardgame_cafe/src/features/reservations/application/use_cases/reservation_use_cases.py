from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Sequence

from features.bookings.domain.models.booking import Booking
from features.reservations.application.interfaces.reservation_repository_interface import (
    ReservationRepositoryInterface,
)
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES
from shared.domain.exceptions import ValidationError

_OPENING_TIME = time(hour=9, minute=0)
_CLOSING_TIME = time(hour=23, minute=0)


@dataclass
class CreateReservationCommand:
    customer_id: int
    table_id: int | None
    start_ts: datetime
    end_ts: datetime
    party_size: int
    notes: Optional[str] = None
    table_ids: list[int] | None = None


class CreateReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, cmd: CreateReservationCommand) -> Booking:
        if cmd.table_id is None:
            raise ValidationError("table_id must be selected before creating reservation")

        if cmd.start_ts.date() != cmd.end_ts.date():
            raise ValidationError(
                "Reservations must start and end on the same day (no overnight bookings)."
            )

        if cmd.start_ts.time() < _OPENING_TIME or cmd.end_ts.time() > _CLOSING_TIME:
            raise ValidationError(
                "Reservations must be within opening hours: 09:00 to 23:00."
            )

        candidate = Booking(
            customer_id=cmd.customer_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
            party_size=cmd.party_size,
            notes=cmd.notes,
        )

        # Reservation compatibility views still include table_id metadata.
        setattr(candidate, "table_id", cmd.table_id)

        existing = self.repo.list_for_table_in_window(
            table_id=cmd.table_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
        )
        if any(
            candidate.start_ts < r.end_ts
            and r.start_ts < candidate.end_ts
            and getattr(r, "status", None) in OVERLAP_BLOCKING_STATUSES
            for r in existing
        ):
            raise ValidationError("Table is not available for the requested timeslot.")

        return self.repo.add(candidate)


class ListReservationsUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self) -> Sequence[Booking]:
        return self.repo.list_all()


class GetReservationByIdUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[Booking]:
        return self.repo.get_by_id(reservation_id)


class CancelReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[Booking]:
        reservation = self.repo.get_by_id(reservation_id)
        if reservation is None:
            return None
        reservation.cancel()
        return self.repo.update(reservation)


class SeatReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[Booking]:
        reservation = self.repo.get_by_id(reservation_id)
        if reservation is None:
            return None
        reservation.seat()
        return self.repo.update(reservation)


class CompleteReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[Booking]:
        reservation = self.repo.get_by_id(reservation_id)
        if reservation is None:
            return None
        reservation.complete()
        return self.repo.update(reservation)


class MarkReservationNoShowUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[Booking]:
        reservation = self.repo.get_by_id(reservation_id)
        if reservation is None:
            return None
        reservation.mark_no_show()
        return self.repo.update(reservation)


class ListConfirmedReservationsUseCase:
    """Workflow 2 — View all confirmed (pending seating) reservations.
 
    'confirmed' is the initial status a booking gets on creation.
    These are the reservations a steward needs to action — seat, cancel, or mark no-show.
    """
 
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo
 
    def execute(self) -> Sequence[Booking]:
        # Pending filter: only include confirmed reservations for today
        today = datetime.utcnow().date()
        return [
            r for r in self.repo.list_all()
            if r.status == "confirmed" and r.start_ts.date() == today
        ]
 
 
class ListSeatedReservationsUseCase:
    """Returns all currently seated reservations.
 
    Useful for the steward dashboard to see who is currently in the cafe.
    """
 
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo
 
    def execute(self) -> Sequence[Booking]:
        return [
            r for r in self.repo.list_all()
            if r.status == "seated"
        ]
 
 
class ListActiveReservationsUseCase:
    """Returns confirmed + seated reservations combined.
 
    The main steward view — everything that still needs attention.
    """
 
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo
 
    def execute(self) -> Sequence[Booking]:
        return [
            r for r in self.repo.list_all()
            if r.status in ("confirmed", "seated")
        ]
 

