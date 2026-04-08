from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.reservations.application.interfaces.reservation_lookup_repository_interface import (
    ReservationLookupRepositoryInterface,
)
from features.tables.infrastructure.database.table_db import TableDB
from shared.infrastructure import db


class SqlAlchemyReservationLookupRepository(ReservationLookupRepositoryInterface):
    def __init__(self, session: Optional[Session] = None) -> None:
        self.session = session or db.session

    def list_tables(self) -> Sequence[dict]:
        rows = self.session.query(TableDB).order_by(TableDB.table_nr.asc()).all()
        return [
            {
                "id": row.id,
                "table_nr": row.table_nr,
                "capacity": row.capacity,
                "status": row.status,
            }
            for row in rows
        ]

    def list_games(self) -> Sequence[dict]:
        rows = self.session.query(GameDB).order_by(GameDB.title.asc()).all()
        return [{"id": row.id, "title": row.title} for row in rows]

    def list_game_copies(self) -> Sequence[dict]:
        rows = self.session.query(GameCopyDB).order_by(GameCopyDB.id.asc()).all()
        return [
            {
                "id": row.id,
                "game_id": row.game_id,
                "copy_code": row.copy_code,
                "status": row.status,
            }
            for row in rows
        ]
