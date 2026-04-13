from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from features.games.domain.models.game import Game
from features.games.domain.models.game_copy import GameCopy
from features.games.infrastructure.repositories.game_copy_repository import (
    GameCopyRepositoryImpl,
)
from features.games.infrastructure.repositories.game_repository import GameRepository
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
def copy_repo(app):
    return GameCopyRepositoryImpl()


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


def test_add_and_get_game_copy(app, game_repo, copy_repo):
    game = _create_game(game_repo)

    created = copy_repo.add(
        GameCopy(
            game_id=game.id,
            copy_code="CATAN-001",
            status="available",
            location="Shelf A",
        )
    )

    fetched = copy_repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.copy_code == "CATAN-001"


def test_list_all_returns_inserted_copies(app, game_repo, copy_repo):
    game = _create_game(game_repo)

    copy_repo.add(GameCopy(game_id=game.id, copy_code="CATAN-001"))
    copy_repo.add(GameCopy(game_id=game.id, copy_code="CATAN-002"))

    copies = copy_repo.list_all()

    assert len(copies) == 2
    assert {copy.copy_code for copy in copies} == {"CATAN-001", "CATAN-002"}


def test_update_persists_status_location_and_condition_note(app, game_repo, copy_repo):
    game = _create_game(game_repo)
    created = copy_repo.add(GameCopy(game_id=game.id, copy_code="CATAN-001"))

    created.status = "maintenance"
    created.location = "Repair Shelf"
    created.condition_note = "Missing one meeple"

    updated = copy_repo.update(created)

    assert updated.status == "maintenance"
    assert updated.location == "Repair Shelf"
    assert updated.condition_note == "Missing one meeple"


def test_add_duplicate_copy_code_raises_integrity_error(app, game_repo, copy_repo):
    game = _create_game(game_repo)

    copy_repo.add(GameCopy(game_id=game.id, copy_code="CATAN-001"))

    with pytest.raises(IntegrityError):
        copy_repo.add(GameCopy(game_id=game.id, copy_code="CATAN-001"))

    db.session.rollback()
