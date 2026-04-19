from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from features.reservations.application.interfaces.reservation_repository_interface import (
    ReservationRepositoryInterface,
)
from features.users.application.interfaces.user_repository_interface import (
    UserRepositoryInterface,
)


@dataclass(frozen=True)
class BrowseStewardReservationsQuery:
    statuses: Optional[tuple[str, ...]] = None
    reservation_date: Optional[date] = None


@dataclass(frozen=True)
class StewardReservationBrowseItem:
    id: int
    customer_id: int
    customer_name: Optional[str]
    customer_email: Optional[str]
    table_id: Optional[int]
    start_ts: object
    end_ts: object
    party_size: int
    status: str
    notes: Optional[str]


class BrowseStewardReservationsUseCase:
    def __init__(
        self,
        reservation_repo: ReservationRepositoryInterface,
        user_repo: UserRepositoryInterface,
    ):
        self.reservation_repo = reservation_repo
        self.user_repo = user_repo

    def execute(self, query: BrowseStewardReservationsQuery) -> Sequence[StewardReservationBrowseItem]:
        reservations = list(self.reservation_repo.list_all())

        if query.statuses:
            accepted = set(query.statuses)
            reservations = [r for r in reservations if r.status in accepted]

        if query.reservation_date is not None:
            reservations = [
                r for r in reservations
                if getattr(r, "start_ts", None) and r.start_ts.date() == query.reservation_date
            ]

        user_ids = {r.customer_id for r in reservations}
        users = {user_id: self.user_repo.get_by_id(user_id) for user_id in user_ids}

        return [
            StewardReservationBrowseItem(
                id=r.id,
                customer_id=r.customer_id,
                customer_name=getattr(users.get(r.customer_id), "name", None),
                customer_email=getattr(users.get(r.customer_id), "email", None),
                table_id=getattr(r, "table_id", None),
                start_ts=r.start_ts,
                end_ts=r.end_ts,
                party_size=r.party_size,
                status=r.status,
                notes=r.notes,
            )
            for r in reservations
        ]
