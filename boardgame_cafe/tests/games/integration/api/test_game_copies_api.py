import pytest

from features.games.presentation.api.game_copy_routes import bp as game_copy_bp
from shared.infrastructure import db
from src.app import create_app


@pytest.fixture
def app():
    app = create_app("testing")

    if "game_copies" not in app.blueprints:
        app.register_blueprint(game_copy_bp)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_game(client, title: str = "Catan") -> int:
    response = client.post(
        "/api/games/",
        json={
            "title": title,
            "min_players": 2,
            "max_players": 4,
            "playtime_min": 60,
            "complexity": 2.5,
        },
    )
    assert response.status_code == 201
    return response.get_json()["id"]


def test_create_and_get_game_copy(client):
    create_response = client.post(
        "/api/game-copies/",
        json={
            "game_id": 1,
            "copy_code": "CATAN-001",
            "status": "available",
            "location": "Shelf A",
        },
    )
    assert create_response.status_code == 201
    created = create_response.get_json()

    get_response = client.get(f"/api/game-copies/{created['id']}")
    assert get_response.status_code == 200
    fetched = get_response.get_json()

    assert fetched["copy_code"] == "CATAN-001"
    assert fetched["status"] == "available"


def test_create_game_copy_rejects_invalid_payload(client):
    response = client.post(
        "/api/game-copies/",
        json={
            "game_id": 0,
            "copy_code": "   ",
            "status": "lost",
        },
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Validation failed"


def test_get_missing_game_copy_returns_404(client):
    response = client.get("/api/game-copies/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Game copy not found"


def test_patch_status_updates_game_copy(client):
    create_response = client.post(
        "/api/game-copies/",
        json={
            "game_id": 1,
            "copy_code": "CATAN-001",
            "status": "available",
        },
    )
    copy_id = create_response.get_json()["id"]

    response = client.patch(
        f"/api/game-copies/{copy_id}/status",
        json={"action": "reserve"},
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "reserved"


def test_patch_status_rejects_invalid_action(client):
    create_response = client.post(
        "/api/game-copies/",
        json={"game_id": 1, "copy_code": "CATAN-001"},
    )
    copy_id = create_response.get_json()["id"]

    response = client.patch(
        f"/api/game-copies/{copy_id}/status",
        json={"action": "repair"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Validation failed"


def test_patch_location_updates_game_copy(client):
    create_response = client.post(
        "/api/game-copies/",
        json={"game_id": 1, "copy_code": "CATAN-001"},
    )
    copy_id = create_response.get_json()["id"]

    response = client.patch(
        f"/api/game-copies/{copy_id}/location",
        json={"location": "Shelf B"},
    )

    assert response.status_code == 200
    assert response.get_json()["location"] == "Shelf B"


def test_patch_condition_note_updates_game_copy(client):
    create_response = client.post(
        "/api/game-copies/",
        json={"game_id": 1, "copy_code": "CATAN-001"},
    )
    copy_id = create_response.get_json()["id"]

    response = client.patch(
        f"/api/game-copies/{copy_id}/condition-note",
        json={"condition_note": "Slightly worn box"},
    )

    assert response.status_code == 200
    assert response.get_json()["condition_note"] == "Slightly worn box"


def test_create_duplicate_copy_code_returns_conflict(client):
    game_id = _create_game(client)

    first = client.post(
        "/api/game-copies/",
        json={"game_id": game_id, "copy_code": "CATAN-DUP-001"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/game-copies/",
        json={"game_id": game_id, "copy_code": "CATAN-DUP-001"},
    )

    assert second.status_code == 409
    assert second.get_json()["error"] == "copy_code already exists"


def test_game_copy_status_lifecycle_flow(client):
    game_id = _create_game(client, title="Azul")

    create_response = client.post(
        "/api/game-copies/",
        json={"game_id": game_id, "copy_code": "AZUL-001", "status": "available"},
    )
    assert create_response.status_code == 201
    copy_id = create_response.get_json()["id"]

    reserve_response = client.patch(
        f"/api/game-copies/{copy_id}/status", json={"action": "reserve"}
    )
    assert reserve_response.status_code == 200
    assert reserve_response.get_json()["status"] == "reserved"

    use_response = client.patch(
        f"/api/game-copies/{copy_id}/status", json={"action": "use"}
    )
    assert use_response.status_code == 200
    assert use_response.get_json()["status"] == "in_use"

    return_response = client.patch(
        f"/api/game-copies/{copy_id}/status", json={"action": "return"}
    )
    assert return_response.status_code == 200
    assert return_response.get_json()["status"] == "available"

    maintenance_response = client.patch(
        f"/api/game-copies/{copy_id}/status", json={"action": "maintenance"}
    )
    assert maintenance_response.status_code == 200
    assert maintenance_response.get_json()["status"] == "maintenance"
