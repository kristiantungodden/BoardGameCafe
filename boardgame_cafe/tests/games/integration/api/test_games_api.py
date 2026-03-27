import pytest
from src.app import create_app
from shared.infrastructure import db

@pytest.fixture
def app():
    """Create a Flask app configured for testing with in-memory DB."""
    app = create_app("testing")  # uses TestingConfig with sqlite:///:memory:

    with app.app_context():
        db.create_all()  # create tables
        yield app
        db.session.remove()
        db.drop_all()  # clean up after tests

@pytest.fixture
def client(app):
    return app.test_client()


def test_create_and_get_game(client):
    # 1. Create a game
    response = client.post("/api/games/", json={
        "title": "Catan",
        "min_players": 3,
        "max_players": 4,
        "playtime_min": 90,
        "complexity": 2.5,
        "description": "Classic strategy game",
        "image_url": None
    })
    assert response.status_code == 201
    data = response.get_json()
    game_id = data["id"]
    assert data["title"] == "Catan"

    # 2. Get the same game
    response = client.get(f"/api/games/{game_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Catan"
    assert data["min_players"] == 3
    assert data["max_players"] == 4
    assert data["playtime_min"] == 90
    assert float(data["complexity"]) == 2.5


def test_get_all_games(client):
    # Create 2 games
    client.post("/api/games/", json={
        "title": "Catan",
        "min_players": 3,
        "max_players": 4,
        "playtime_min": 60,
        "complexity": 2.5,
        "description": "Strategy game"
    })
    client.post("/api/games/", json={
        "title": "Monopoly",
        "min_players": 2,
        "max_players": 6,
        "playtime_min": 90,
        "complexity": 1.5,
        "description": "Family game"
    })

    # Fetch all games
    response = client.get("/api/games/")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) >= 2
    titles = [g["title"] for g in data]
    assert "Catan" in titles
    assert "Monopoly" in titles