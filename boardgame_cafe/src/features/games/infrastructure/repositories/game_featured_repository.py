from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.game_rating_db import GameRatingDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from shared.infrastructure import db


@dataclass(frozen=True)
class TopRatedGameResult:
    game: GameDB
    average_rating: float
    rating_count: int


@dataclass(frozen=True)
class MostBorrowedGameResult:
    game: GameDB
    borrow_count: int


class SqlAlchemyGameFeaturedRepository:
    def __init__(self, session=None):
        self.session = session or db.session

    def find_top_rated_last_month(self) -> Optional[TopRatedGameResult]:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        row = (
            self.session.query(
                GameDB,
                func.avg(GameRatingDB.stars).label("avg_rating"),
                func.count(GameRatingDB.id).label("rating_count"),
            )
            .join(GameRatingDB, GameRatingDB.game_id == GameDB.id)
            .filter(GameRatingDB.created_at >= since)
            .group_by(GameDB.id)
            .order_by(func.avg(GameRatingDB.stars).desc(), func.count(GameRatingDB.id).desc(), GameDB.id.asc())
            .first()
        )
        if row is None:
            return None
        game, avg_rating, rating_count = row
        return TopRatedGameResult(
            game=game,
            average_rating=float(avg_rating or 0),
            rating_count=int(rating_count or 0),
        )

    def find_most_borrowed_last_month(self) -> Optional[MostBorrowedGameResult]:
        since = datetime.now(timezone.utc) - timedelta(days=30)
        row = (
            self.session.query(
                GameDB,
                func.count(GameReservationDB.id).label("borrow_count"),
            )
            .join(GameReservationDB, GameReservationDB.requested_game_id == GameDB.id)
            .join(BookingDB, BookingDB.id == GameReservationDB.booking_id)
            .filter(BookingDB.start_ts >= since)
            .group_by(GameDB.id)
            .order_by(func.count(GameReservationDB.id).desc(), GameDB.id.asc())
            .first()
        )
        if row is None:
            return None
        game, borrow_count = row
        return MostBorrowedGameResult(game=game, borrow_count=int(borrow_count or 0))
