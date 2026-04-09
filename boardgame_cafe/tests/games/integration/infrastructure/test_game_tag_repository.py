from decimal import Decimal

import pytest

from features.games.domain.models.game import Game
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.games.infrastructure.repositories.game_tag_repository import GameTagRepository
from src.app import create_app
from shared.infrastructure import db


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
def tag_repo(app):
    return GameTagRepository()


def test_create_and_list_tags(tag_repo):
    created = tag_repo.create_tag("Strategy")

    assert created.id is not None
    assert created.name == "strategy"

    tags = tag_repo.list_tags()
    assert any(tag.id == created.id for tag in tags)


def test_attach_list_and_remove_tag_link(game_repo, tag_repo):
    game = game_repo.add(
        Game(
            id=None,
            title="Azul",
            min_players=2,
            max_players=4,
            playtime_min=45,
            complexity=Decimal("2.0"),
        )
    )
    tag = tag_repo.create_tag("Abstract")

    link = tag_repo.attach_tag_to_game(game.id, tag.id)
    assert link.id is not None
    assert link.game_id == game.id
    assert link.game_tag_id == tag.id

    game_tags = tag_repo.list_tags_for_game(game.id)
    assert len(game_tags) == 1
    assert game_tags[0].id == tag.id

    removed = tag_repo.remove_tag_from_game(game.id, tag.id)
    assert removed is True

    game_tags_after = tag_repo.list_tags_for_game(game.id)
    assert game_tags_after == []
