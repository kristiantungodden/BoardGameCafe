from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

from application.interfaces.repositories.reservation import ReservationRepository
from domain.exceptions import ValidationError
from domain.models.reservation import TableReservation


@dataclass
class CreateReservationCommand:
    customer_id: int
    table_id: int
    start_ts: datetime
    end_ts: datetime
    party_size: int
    notes: Optional[str] = None


class CreateReservationUseCase:
    def __init__(self, repo: ReservationRepository):
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
        if any(candidate.overlaps(r) for r in existing):
            raise ValidationError("Table is not available for the requested timeslot.")

        return self.repo.add(candidate)


class ListReservationsUseCase:
    def __init__(self, repo: ReservationRepository):
        self.repo = repo

    def execute(self) -> Sequence[TableReservation]:
        return self.repo.list_all()


class GetReservationByIdUseCase:
    def __init__(self, repo: ReservationRepository):
        self.repo = repo

    def execute(self, reservation_id: int) -> Optional[TableReservation]:
        return self.repo.get_by_id(reservation_id)