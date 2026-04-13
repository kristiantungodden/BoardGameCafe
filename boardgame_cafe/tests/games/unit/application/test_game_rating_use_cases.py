import pytest

from features.games.application.use_cases.game_rating_use_cases import (
    CreateGameRatingCommand,
    CreateGameRatingUseCase,
    GetAverageRatingByGameIdUseCase,
    GetRatingsByGameIdUseCase,
)
from features.games.domain.models.game_rating import GameRating


class FakeGameRatingRepository:
    def __init__(self):
        self._ratings = []
        self._next_id = 1

    def create(self, rating: GameRating) -> GameRating:
        created = GameRating(
            id=self._next_id,
            customer_id=rating.customer_id,
            game_id=rating.game_id,
            stars=rating.stars,
            comment=rating.comment,
            created_at=rating.created_at,
        )
        self._ratings.append(created)
        self._next_id += 1
        return created

    def get_by_game_id(self, game_id: int) -> list[GameRating]:
        return [rating for rating in self._ratings if rating.game_id == game_id]

    def get_average_by_game_id(self, game_id: int):
        stars = [rating.stars for rating in self._ratings if rating.game_id == game_id]
        if not stars:
            return None
        return sum(stars) / len(stars)

    def get_rating_by_customer_and_game(self, customer_id: int, game_id: int):
        for rating in self._ratings:
            if rating.customer_id == customer_id and rating.game_id == game_id:
                return rating
        return None


def test_create_game_rating_use_case_creates_rating():
    repo = FakeGameRatingRepository()
    use_case = CreateGameRatingUseCase(repo)

    created = use_case.execute(
        CreateGameRatingCommand(
            customer_id=1,
            game_id=1,
            stars=5,
            comment="Great game",
        )
    )

    assert created.id == 1
    assert created.customer_id == 1
    assert created.game_id == 1
    assert created.stars == 5


def test_create_game_rating_use_case_rejects_duplicate_rating():
    repo = FakeGameRatingRepository()
    use_case = CreateGameRatingUseCase(repo)

    use_case.execute(
        CreateGameRatingCommand(customer_id=1, game_id=1, stars=4, comment=None)
    )

    with pytest.raises(ValueError, match="already rated"):
        use_case.execute(
            CreateGameRatingCommand(customer_id=1, game_id=1, stars=5, comment=None)
        )


def test_create_game_rating_use_case_rejects_invalid_stars():
    repo = FakeGameRatingRepository()
    use_case = CreateGameRatingUseCase(repo)

    with pytest.raises(ValueError, match="stars must be an integer between 1 and 5"):
        use_case.execute(
            CreateGameRatingCommand(customer_id=1, game_id=1, stars=6, comment=None)
        )


def test_get_ratings_by_game_id_use_case_validates_game_id():
    repo = FakeGameRatingRepository()
    use_case = GetRatingsByGameIdUseCase(repo)

    with pytest.raises(ValueError, match="game_id must be greater than 0"):
        use_case.execute(0)


def test_get_average_rating_by_game_id_use_case_validates_game_id():
    repo = FakeGameRatingRepository()
    use_case = GetAverageRatingByGameIdUseCase(repo)

    with pytest.raises(ValueError, match="game_id must be greater than 0"):
        use_case.execute(0)


def test_get_average_rating_by_game_id_returns_average():
    repo = FakeGameRatingRepository()
    create_use_case = CreateGameRatingUseCase(repo)
    average_use_case = GetAverageRatingByGameIdUseCase(repo)

    create_use_case.execute(
        CreateGameRatingCommand(customer_id=1, game_id=2, stars=4, comment=None)
    )
    create_use_case.execute(
        CreateGameRatingCommand(customer_id=2, game_id=2, stars=2, comment=None)
    )

    avg = average_use_case.execute(2)

    assert avg == 3.0
