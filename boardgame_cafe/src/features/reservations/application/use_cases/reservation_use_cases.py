from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, Sequence

from features.reservations.application.interfaces.reservation_repository_interface import ReservationRepositoryInterface
from shared.domain.exceptions import ValidationError
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES
from features.reservations.domain.models.reservation import TableReservation

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


class CreateReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, cmd: CreateReservationCommand) -> TableReservation:
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

        candidate = TableReservation(
            customer_id=cmd.customer_id,
            table_id=cmd.table_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
            party_size=cmd.party_size,
            notes=cmd.notes,
        )

        existing = self.repo.list_for_table_in_window(
            table_id=cmd.table_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
        )
        if any(
            candidate.overlaps(r) and r.status in OVERLAP_BLOCKING_STATUSES
            for r in existing
        ):
            raise ValidationError("Table is not available for the requested timeslot.")

        return self.repo.add(candidate)


class ListReservationsUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self) -> Sequence[TableReservation]:
        return self.repo.list_all()


class GetReservationByIdUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[TableReservation]:
        return self.repo.get_by_id(reservation_id)


class CancelReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[TableReservation]:
        reservation = self.repo.get_by_id(reservation_id)
        if reservation is None:
            return None

        reservation.cancel()
        return self.repo.update(reservation)


class SeatReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[TableReservation]:
        reservation = self.repo.get_by_id(reservation_id)
        if reservation is None:
            return None

        reservation.seat()
        return self.repo.update(reservation)


class CompleteReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[TableReservation]:
        reservation = self.repo.get_by_id(reservation_id)
        if reservation is None:
            return None

        reservation.complete()
        return self.repo.update(reservation)


class MarkReservationNoShowUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[TableReservation]:
        reservation = self.repo.get_by_id(reservation_id)
        if reservation is None:
            return None

        reservation.mark_no_show()
        return self.repo.update(reservation)