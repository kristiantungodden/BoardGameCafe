from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from features.reservations.application.interfaces.reservation_repository_interface import ReservationRepositoryInterface
from shared.domain.exceptions import ValidationError
from features.reservations.domain.models.reservation import TableReservation

_OVERLAP_BLOCKING_STATUSES = {"confirmed", "seated"}


@dataclass
class CreateReservationCommand:
    customer_id: int
    table_id: int
    start_ts: datetime
    end_ts: datetime
    party_size: int
    notes: Optional[str] = None


class CreateReservationUseCase:
    def __init__(self, repo: ReservationRepositoryInterface):
        self.repo = repo

    def execute(self, cmd: CreateReservationCommand) -> TableReservation:
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
            candidate.overlaps(r) and r.status in _OVERLAP_BLOCKING_STATUSES
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