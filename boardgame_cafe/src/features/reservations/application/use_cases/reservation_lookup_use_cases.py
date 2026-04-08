from __future__ import annotations

from features.reservations.application.interfaces.reservation_lookup_repository_interface import (
    ReservationLookupRepositoryInterface,
)


class GetReservationLookupUseCase:
    def __init__(self, repository: ReservationLookupRepositoryInterface):
        self.repository = repository

    def execute(self) -> dict:
        return {
            "tables": list(self.repository.list_tables()),
            "games": list(self.repository.list_games()),
            "game_copies": list(self.repository.list_game_copies()),
        }
