from datetime import datetime
from typing import Optional

from features.reservations.application.interfaces.available_game_copy_repository_interface import (
    AvailableGameCopyRepositoryInterface,
)
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES
from shared.domain.exceptions import ValidationError
from shared.infrastructure import db


class SqlAlchemyAvailableGameCopyRepository(AvailableGameCopyRepositoryInterface):
    """SQLAlchemy implementation for querying available game copies."""

    def __init__(self, session=None):
        self.session = session or db.session

    def get_blocked_copy_ids(self, start_ts: datetime, end_ts: datetime) -> set[int]:
        """Get game copy IDs blocked during the given time window."""
        rows = (
            self.session.query(GameReservationDB.game_copy_id)
            .join(BookingDB, GameReservationDB.booking_id == BookingDB.id)
            .filter(BookingDB.status.in_(OVERLAP_BLOCKING_STATUSES))
            .filter(BookingDB.start_ts < end_ts)
            .filter(start_ts < BookingDB.end_ts)
            .all()
        )
        return {row[0] for row in rows}

    def find_available_copy_id(
        self, game_id: int, start_ts: datetime, end_ts: datetime
    ) -> Optional[int]:
        """Find the first available copy for a game that's not blocked during the window."""
        blocked = self.get_blocked_copy_ids(start_ts, end_ts)
        query = (
            self.session.query(GameCopyDB)
            .filter(GameCopyDB.status == "available")
            .filter(GameCopyDB.game_id == game_id)
        )
        if blocked:
            query = query.filter(~GameCopyDB.id.in_(blocked))

        candidate = query.order_by(GameCopyDB.id.asc()).first()
        return candidate.id if candidate else None

    def validate_copy_available(
        self, game_copy_id: int, game_id: int, start_ts: datetime, end_ts: datetime
    ) -> bool:
        """Check if a specific copy is available for the game during the window."""
        copy = self.session.get(GameCopyDB, game_copy_id)
        if copy is None:
            raise ValidationError("Selected game copy does not exist")
        if copy.game_id != game_id:
            raise ValidationError("Selected game copy does not match requested game")
        if copy.status != "available":
            raise ValidationError("Selected game copy is not available")

        blocked = self.get_blocked_copy_ids(start_ts, end_ts)
        if game_copy_id in blocked:
            return False

        return True
