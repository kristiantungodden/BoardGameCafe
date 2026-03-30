from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from features.reservations.application.interfaces.game_reservation_repository_interface import (
    GameReservationRepositoryInterface,
)
from features.reservations.domain.models.reservation_game import ReservationGame
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from shared.infrastructure import db


class SqlAlchemyGameReservationRepository(GameReservationRepositoryInterface):
    def __init__(self, session: Optional[Session] = None, auto_commit: bool = True) -> None:
        self.session = session or db.session
        self.auto_commit = auto_commit

    def add(self, reservation_game: ReservationGame) -> ReservationGame:
        row = GameReservationDB(
            table_reservation_id=reservation_game.table_reservation_id,
            requested_game_id=reservation_game.requested_game_id,
            game_copy_id=reservation_game.game_copy_id,
        )
        self.session.add(row)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        return self._to_domain(row)

    def get_by_id(self, reservation_game_id: int) -> Optional[ReservationGame]:
        row = self.session.get(GameReservationDB, reservation_game_id)
        if row is None:
            return None
        return self._to_domain(row)

    def list_for_reservation(self, reservation_id: int) -> Sequence[ReservationGame]:
        rows = (
            self.session.query(GameReservationDB)
            .filter(GameReservationDB.table_reservation_id == reservation_id)
            .order_by(GameReservationDB.id.asc())
            .all()
        )
        return [self._to_domain(row) for row in rows]

    def delete(self, reservation_game_id: int) -> bool:
        row = self.session.get(GameReservationDB, reservation_game_id)
        if row is None:
            return False
        self.session.delete(row)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        return True

    @staticmethod
    def _to_domain(row: GameReservationDB) -> ReservationGame:
        return ReservationGame(
            id=row.id,
            table_reservation_id=row.table_reservation_id,
            requested_game_id=row.requested_game_id,
            game_copy_id=row.game_copy_id,
        )
