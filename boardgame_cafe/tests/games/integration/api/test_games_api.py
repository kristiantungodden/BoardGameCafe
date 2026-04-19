from decimal import Decimal

import pytest
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db
from src.app import create_app

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
    test_client = app.test_client()
    with app.app_context():
        existing = UserDB.query.filter_by(email="games-api-admin@example.com").first()
        if existing is None:
            db.session.add(
                UserDB(
                    role="admin",
                    name="Games API Admin",
                    email="games-api-admin@example.com",
                    password_hash=hash_password("password123"),
                )
            )
            db.session.commit()

    login_response = test_client.post(
        "/api/auth/login",
        json={"email": "games-api-admin@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200
    return test_client


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


def test_create_game_rejects_invalid_payload(client):
    response = client.post(
        "/api/games/",
        json={
            "title": "",
            "min_players": 5,
            "max_players": 3,
            "playtime_min": 0,
            "complexity": -1,
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Validation failed"


def test_get_non_existing_game_returns_404(client):
    response = client.get("/api/games/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Game not found"


def test_update_game_updates_fields(client):
    create_response = client.post(
        "/api/games/",
        json={
            "title": "Catan",
            "min_players": 3,
            "max_players": 4,
            "playtime_min": 90,
            "complexity": 2.5,
            "description": "Classic strategy game",
        },
    )
    game_id = create_response.get_json()["id"]

    response = client.put(
        f"/api/games/{game_id}",
        json={
            "title": "Catan: Revised",
            "min_players": 2,
            "max_players": 4,
            "playtime_min": 100,
            "complexity": Decimal("2.75"),
            "description": "Updated description",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Catan: Revised"
    assert data["min_players"] == 2
    assert data["max_players"] == 4
    assert data["playtime_min"] == 100
    assert float(data["complexity"]) == 2.75
    assert data["description"] == "Updated description"


def test_update_game_rejects_invalid_range(client):
    create_response = client.post(
        "/api/games/",
        json={
            "title": "Catan",
            "min_players": 3,
            "max_players": 4,
            "playtime_min": 90,
            "complexity": 2.5,
        },
    )
    game_id = create_response.get_json()["id"]

    response = client.put(
        f"/api/games/{game_id}",
        json={"min_players": 5, "max_players": 3},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Validation failed"


def test_update_non_existing_game_returns_404(client):
    response = client.put(
        "/api/games/999",
        json={"title": "Missing Game"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Game not found"


def test_delete_game_removes_game(client):
    create_response = client.post(
        "/api/games/",
        json={
            "title": "Catan",
            "min_players": 3,
            "max_players": 4,
            "playtime_min": 90,
            "complexity": 2.5,
        },
    )
    game_id = create_response.get_json()["id"]

    delete_response = client.delete(f"/api/games/{game_id}")
    assert delete_response.status_code == 200

    get_response = client.get(f"/api/games/{game_id}")
    assert get_response.status_code == 404


def test_delete_non_existing_game_returns_404(client):
    response = client.delete("/api/games/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Game not found"


def test_delete_game_with_existing_copies_returns_conflict(client, app):
    create_response = client.post(
        "/api/games/",
        json={
            "title": "Carcassonne",
            "min_players": 2,
            "max_players": 5,
            "playtime_min": 45,
            "complexity": 2.0,
        },
    )
    assert create_response.status_code == 201
    game_id = create_response.get_json()["id"]

    with app.app_context():
        db.session.add(
            GameCopyDB(game_id=game_id, copy_code="CAR-001", status="available")
        )
        db.session.commit()

    delete_response = client.delete(f"/api/games/{game_id}")

    assert delete_response.status_code == 409
    assert (
        delete_response.get_json()["error"]
        == "Cannot delete game with existing copies"
    )


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