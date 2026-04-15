from decimal import Decimal

import pytest

from features.games.infrastructure.database.game_db import GameDB
from features.games.presentation.api.game_rating_routes import bp as game_ratings_bp
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db
from src.app import create_app


@pytest.fixture
def app():
    app = create_app("testing")

    if "game_ratings" not in app.blueprints:
        app.register_blueprint(game_ratings_bp)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_user(email: str) -> int:
    user = UserDB(
        role="customer",
        name="Rating API User",
        email=email,
        password_hash="hashed",
    )
    db.session.add(user)
    db.session.commit()
    return user.id


def _create_game(title: str) -> int:
    game = GameDB(
        title=title,
        min_players=2,
        max_players=4,
        playtime_min=60,
        complexity=Decimal("2.5"),
        description="Test game",
    )
    db.session.add(game)
    db.session.commit()
    return game.id


def test_create_game_rating_returns_201(client, app):
    with app.app_context():
        customer_id = _create_user("api-rating-1@example.com")
        game_id = _create_game("Catan")

    response = client.post(
        "/api/game-ratings/",
        json={
            "customer_id": customer_id,
            "game_id": game_id,
            "stars": 5,
            "comment": "Amazing game",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["customer_id"] == customer_id
    assert body["game_id"] == game_id
    assert body["stars"] == 5


def test_create_game_rating_rejects_invalid_payload(client):
    response = client.post(
        "/api/game-ratings/",
        json={
            "customer_id": 1,
            "game_id": 1,
            "stars": 7,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Validation failed"


def test_create_duplicate_game_rating_rejected(client, app):
    with app.app_context():
        customer_id = _create_user("api-rating-2@example.com")
        game_id = _create_game("Azul")

    first = client.post(
        "/api/game-ratings/",
        json={
            "customer_id": customer_id,
            "game_id": game_id,
            "stars": 4,
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/game-ratings/",
        json={
            "customer_id": customer_id,
            "game_id": game_id,
            "stars": 5,
        },
    )

    assert second.status_code == 400
    assert second.get_json()["error"] == "User has already rated this game"


def test_get_ratings_by_game_id_returns_created_ratings(client, app):
    with app.app_context():
        game_id = _create_game("Wingspan")
        customer_1 = _create_user("api-rating-3@example.com")
        customer_2 = _create_user("api-rating-4@example.com")

    client.post(
        "/api/game-ratings/",
        json={"customer_id": customer_1, "game_id": game_id, "stars": 5},
    )
    client.post(
        "/api/game-ratings/",
        json={"customer_id": customer_2, "game_id": game_id, "stars": 3},
    )

    response = client.get(f"/api/game-ratings/game/{game_id}")

    assert response.status_code == 200
    body = response.get_json()
    assert len(body) == 2
    stars = sorted([entry["stars"] for entry in body])
    assert stars == [3, 5]


def test_get_average_rating_returns_expected_value(client, app):
    with app.app_context():
        game_id = _create_game("Terraforming Mars")
        customer_1 = _create_user("api-rating-5@example.com")
        customer_2 = _create_user("api-rating-6@example.com")

    client.post(
        "/api/game-ratings/",
        json={"customer_id": customer_1, "game_id": game_id, "stars": 4},
    )
    client.post(
        "/api/game-ratings/",
        json={"customer_id": customer_2, "game_id": game_id, "stars": 2},
    )

    response = client.get(f"/api/game-ratings/game/{game_id}/average")

    assert response.status_code == 200
    body = response.get_json()
    assert body["game_id"] == game_id
    assert body["average_rating"] == 3.0


def test_get_average_rating_returns_none_when_no_ratings(client, app):
    with app.app_context():
        game_id = _create_game("No Reviews Yet")

    response = client.get(f"/api/game-ratings/game/{game_id}/average")

    assert response.status_code == 200
    body = response.get_json()
    assert body["game_id"] == game_id
    assert body["average_rating"] is None
