from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from features.games.domain.models.game import Game
from features.games.domain.models.game_rating import GameRating
from features.games.infrastructure.repositories.game_rating_repository import (
    GameRatingRepositoryImpl,
)
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db
from src.app import create_app


@pytest.fixture
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def game_repo(app):
    return GameRepository()


@pytest.fixture
def rating_repo(app):
    return GameRatingRepositoryImpl()


def _create_user(email: str = "rating-user@example.com") -> UserDB:
    user = UserDB(
        role="customer",
        name="Rating User",
        email=email,
        password_hash="hashed",
    )
    db.session.add(user)
    db.session.commit()
    return user


def _create_game(game_repo: GameRepository, title: str = "Catan") -> Game:
    return game_repo.add(
        Game(
            id=None,
            title=title,
            min_players=3,
            max_players=4,
            playtime_min=90,
            complexity=Decimal("2.5"),
            description="Classic strategy game",
        )
    )


def test_create_and_get_rating_by_game_id(app, game_repo, rating_repo):
    user = _create_user("repo-rating-1@example.com")
    game = _create_game(game_repo)

    created = rating_repo.create(
        GameRating(
            id=None,
            customer_id=user.id,
            game_id=game.id,
            stars=5,
            comment="Excellent",
        )
    )

    ratings = rating_repo.get_by_game_id(game.id)

    assert created.id is not None
    assert len(ratings) == 1
    assert ratings[0].stars == 5


def test_get_average_by_game_id_returns_expected_value(app, game_repo, rating_repo):
    user1 = _create_user("repo-rating-2@example.com")
    user2 = _create_user("repo-rating-3@example.com")
    game = _create_game(game_repo, title="Azul")

    rating_repo.create(
        GameRating(id=None, customer_id=user1.id, game_id=game.id, stars=4, comment=None)
    )
    rating_repo.create(
        GameRating(id=None, customer_id=user2.id, game_id=game.id, stars=2, comment=None)
    )

    average = rating_repo.get_average_by_game_id(game.id)

    assert average == 3.0


def test_get_average_by_game_id_returns_none_when_no_ratings(app, game_repo, rating_repo):
    game = _create_game(game_repo, title="No Ratings Yet")

    average = rating_repo.get_average_by_game_id(game.id)

    assert average is None


def test_get_rating_by_customer_and_game_returns_match(app, game_repo, rating_repo):
    user = _create_user("repo-rating-4@example.com")
    game = _create_game(game_repo, title="Ticket to Ride")

    rating_repo.create(
        GameRating(id=None, customer_id=user.id, game_id=game.id, stars=3, comment="OK")
    )

    fetched = rating_repo.get_rating_by_customer_and_game(user.id, game.id)

    assert fetched is not None
    assert fetched.customer_id == user.id
    assert fetched.game_id == game.id
    assert fetched.stars == 3


def test_create_duplicate_rating_raises_integrity_error(app, game_repo, rating_repo):
    user = _create_user("repo-rating-5@example.com")
    game = _create_game(game_repo, title="Splendor")

    rating_repo.create(
        GameRating(id=None, customer_id=user.id, game_id=game.id, stars=4, comment=None)
    )

    with pytest.raises(IntegrityError):
        rating_repo.create(
            GameRating(
                id=None,
                customer_id=user.id,
                game_id=game.id,
                stars=5,
                comment="Changed mind",
            )
        )

    db.session.rollback()
