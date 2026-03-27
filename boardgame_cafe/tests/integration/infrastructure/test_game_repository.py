import pytest
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.games.domain.models.game import Game
from src.app import create_app
from shared.infrastructure import db  # import the single db instance

@pytest.fixture(scope="module")
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
    games = repo.get_all()
    assert len(games) > 0
    for g in games:
        assert g.id is not None
        assert isinstance(g.title, str)