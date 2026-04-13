from dataclasses import dataclass

from features.games.domain.models.game_rating import GameRating


@dataclass
class CreateGameRatingCommand:
    customer_id: int
    game_id: int
    stars: int
    comment: str | None = None


class CreateGameRatingUseCase:
    def __init__(self, repository):
        self.repository = repository

    def execute(self, command: CreateGameRatingCommand) -> GameRating:
        game_rating = GameRating(
            id=None,
            customer_id=command.customer_id,
            game_id=command.game_id,
            stars=command.stars,
            comment=command.comment,
        )

        game_rating.validate()

        existing = self.repository.get_rating_by_customer_and_game(
            command.customer_id,
            command.game_id,
        )

        if existing:
            raise ValueError("User has already rated this game")

        return self.repository.create(game_rating)


class GetRatingsByGameIdUseCase:
    def __init__(self, repository):
        self.repository = repository

    def execute(self, game_id: int):
        if game_id <= 0:
            raise ValueError("game_id must be greater than 0")

        return self.repository.get_by_game_id(game_id)


class GetAverageRatingByGameIdUseCase:
    def __init__(self, repository):
        self.repository = repository

    def execute(self, game_id: int):
        if game_id <= 0:
            raise ValueError("game_id must be greater than 0")

        return self.repository.get_average_by_game_id(game_id)