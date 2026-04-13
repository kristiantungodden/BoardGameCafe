from features.games.domain.models.game_rating import GameRating
from features.games.infrastructure.database.game_rating_db import GameRatingDB
from shared.infrastructure import db


class GameRatingRepositoryImpl:
    def create(self, rating: GameRating) -> GameRating:
        rating_db = GameRatingDB(
            customer_id=rating.customer_id,
            game_id=rating.game_id,
            stars=rating.stars,
            comment=rating.comment,
        )

        db.session.add(rating_db)
        db.session.commit()

        return GameRating(
            id=rating_db.id,
            customer_id=rating_db.customer_id,
            game_id=rating_db.game_id,
            stars=rating_db.stars,
            comment=rating_db.comment,
            created_at=rating_db.created_at,
        )

    def get_by_game_id(self, game_id: int) -> list[GameRating]:
        ratings_db = (
            GameRatingDB.query
            .filter_by(game_id=game_id)
            .order_by(GameRatingDB.created_at.desc())
            .all()
        )

        return [
            GameRating(
                id=r.id,
                customer_id=r.customer_id,
                game_id=r.game_id,
                stars=r.stars,
                comment=r.comment,
                created_at=r.created_at,
            )
            for r in ratings_db
        ]

    def get_average_by_game_id(self, game_id: int):
        result = db.session.query(
            db.func.avg(GameRatingDB.stars)
        ).filter_by(game_id=game_id).scalar()

        return float(result) if result is not None else None

    def get_rating_by_customer_and_game(self, customer_id: int, game_id: int):
        rating_db = GameRatingDB.query.filter_by(
            customer_id=customer_id,
            game_id=game_id,
        ).first()

        if not rating_db:
            return None

        return GameRating(
            id=rating_db.id,
            customer_id=rating_db.customer_id,
            game_id=rating_db.game_id,
            stars=rating_db.stars,
            comment=rating_db.comment,
            created_at=rating_db.created_at,
        )