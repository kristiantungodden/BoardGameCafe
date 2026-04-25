from datetime import datetime

from features.reservations.application.interfaces.available_game_copy_repository_interface import (
    AvailableGameCopyRepositoryInterface,
)
from features.reservations.application.interfaces.available_table_repository_interface import (
    AvailableTableRepositoryInterface,
)
from shared.infrastructure import db


class GetBookingAvailabilityUseCase:
    """Use case for retrieving booking availability data (tables and games)."""

    def __init__(
        self,
        available_table_repo: AvailableTableRepositoryInterface,
        available_copy_repo: AvailableGameCopyRepositoryInterface,
    ):
        self.available_table_repo = available_table_repo
        self.available_copy_repo = available_copy_repo

    def execute(self, start_ts: datetime, end_ts: datetime, party_size: int) -> dict:
        """Get availability data for the given time window and party size."""
        # Import here to avoid circular imports
        from features.tables.infrastructure.database.table_db import TableDB
        from features.games.infrastructure.database.game_db import GameDB
        from features.games.infrastructure.database.game_copy_db import GameCopyDB

        session = db.session()

        # Get suggested table
        blocked_tables = self.available_table_repo.get_blocked_table_ids(start_ts, end_ts)
        table_query = (
            session.query(TableDB)
            .filter(TableDB.status == "available")
            .filter(TableDB.capacity >= party_size)
        )
        if blocked_tables:
            table_query = table_query.filter(~TableDB.id.in_(blocked_tables))

        suggested_table = table_query.order_by(TableDB.capacity.asc(), TableDB.id.asc()).first()

        # Get available games and copies
        blocked_copies = self.available_copy_repo.get_blocked_copy_ids(start_ts, end_ts)
        available_copies_q = session.query(GameCopyDB).filter(GameCopyDB.status == "available")
        if blocked_copies:
            available_copies_q = available_copies_q.filter(~GameCopyDB.id.in_(blocked_copies))
        available_copies = available_copies_q.all()

        available_game_ids = {row.game_id for row in available_copies}
        games = session.query(GameDB).order_by(GameDB.title.asc()).all()
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
                    "table_nr": suggested_table.table_nr,
                    "capacity": suggested_table.capacity,
                    "status": suggested_table.status,
                }
                if suggested_table
                else None
            ),
            "games": game_availability,
        }
