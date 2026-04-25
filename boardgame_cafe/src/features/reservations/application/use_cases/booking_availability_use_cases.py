from datetime import datetime

from features.reservations.application.interfaces.available_game_copy_repository_interface import (
    AvailableGameCopyRepositoryInterface,
)
from features.reservations.application.interfaces.available_table_repository_interface import (
    AvailableTableRepositoryInterface,
)
from features.games.application.interfaces.game_repository_interface import (
    GameRepositoryInterface,
)
from features.tables.application.interfaces.table_repository import TableRepository as TableRepositoryInterface
from features.games.application.interfaces.game_copy_repository_interface import GameCopyRepository as GameCopyRepositoryInterface


class GetBookingAvailabilityUseCase:
    """Use case for retrieving booking availability data (tables and games)."""

    def __init__(
        self,
        available_table_repo: AvailableTableRepositoryInterface,
        available_copy_repo: AvailableGameCopyRepositoryInterface,
        table_repo: TableRepositoryInterface,
        game_copy_repo: GameCopyRepositoryInterface,
        game_repo: GameRepositoryInterface,
    ):
        self.available_table_repo = available_table_repo
        self.available_copy_repo = available_copy_repo
        self.table_repo = table_repo
        self.game_copy_repo = game_copy_repo
        self.game_repo = game_repo

    def execute(self, start_ts: datetime, end_ts: datetime, party_size: int) -> dict:
        """Get availability data for the given time window and party size."""
        # Get suggested table
        suggested_table_id = self.available_table_repo.find_best_available_table(
            party_size=party_size,
            start_ts=start_ts,
            end_ts=end_ts,
        )
        suggested_table = (
            self.table_repo.get_by_id(suggested_table_id)
            if suggested_table_id is not None
            else None
        )

        # Get available games and copies
        available_copy_ids = self._get_available_copy_ids(start_ts, end_ts)
        available_copies = [
            copy for copy in (self.game_copy_repo.list_all() or []) if copy.id in available_copy_ids
        ]

        available_game_ids = {row.game_id for row in available_copies}
        games = self.game_repo.get_all_games() or []
        copies_by_game = {}
        for copy in available_copies:
            copies_by_game.setdefault(copy.game_id, []).append(copy.id)

        game_availability = [
            {
                "id": game.id,
                "title": game.title,
                "price_cents": int(getattr(game, "price_cents", 0) or 0),
                "available": game.id in available_game_ids,
                "suggested_copy_id": (
                    sorted(copies_by_game.get(game.id, []))[0]
                    if copies_by_game.get(game.id)
                    else None
                ),
            }
            for game in games
        ]

        return {
            "suggested_table": (
                {
                    "id": suggested_table.id,
                    "table_nr": getattr(suggested_table, "table_nr", getattr(suggested_table, "number", None)),
                    "capacity": suggested_table.capacity,
                    "status": suggested_table.status,
                }
                if suggested_table
                else None
            ),
            "games": game_availability,
        }

    def _get_available_copy_ids(self, start_ts: datetime, end_ts: datetime) -> set[int]:
        blocked_copies = self.available_copy_repo.get_blocked_copy_ids(start_ts, end_ts)
        all_copy_ids = {copy.id for copy in (self.game_copy_repo.list_all() or []) if copy.id is not None}
        if not blocked_copies:
            return set(all_copy_ids)
        return {copy_id for copy_id in all_copy_ids if copy_id not in blocked_copies}
