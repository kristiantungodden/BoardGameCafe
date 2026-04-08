import pytest
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.games.domain.models.game import Game
from src.app import create_app
from shared.infrastructure import db  # import the single db instance

@pytest.fixture
def app():
    """Provide a Flask app with testing config and app context."""
    app = create_app("testing")  # uses TestingConfig (sqlite:///:memory:)
    with app.app_context():
        db.create_all()  # create tables
        yield app
        db.session.remove()
        db.drop_all()  # cleanup

@pytest.fixture
def repo(app):
    """Provide a repository instance."""
    return GameRepository()

def test_add_and_get_game(app, repo):
    game = Game(
        id=None,
        title="Catan",
        min_players=3,
        max_players=4,
        playtime_min=60,
        complexity=2.5,
        description="Classic strategy game"
    )
    created = repo.add(game)

    assert created.id is not None
    fetched = repo.get_by_id(created.id)
    assert fetched.title == "Catan"
    assert fetched.id == created.id

def test_get_all_games(app, repo):
    created = repo.add(
        Game(
            id=None,
            title="Terraforming Mars",
            min_players=1,
            max_players=5,
            playtime_min=120,
            complexity=3.2,
            description="Engine building game",
        )
    )

    games = repo.get_all()
    assert any(game.id == created.id for game in games)
    assert any(game.title == "Terraforming Mars" for game in games)
    for g in games:
        assert g.id is not None
        assert isinstance(g.title, str)