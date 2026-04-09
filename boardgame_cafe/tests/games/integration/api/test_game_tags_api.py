import pytest

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
def client(app):
    return app.test_client()


def test_create_and_list_tags(client):
    create_response = client.post("/api/games/tags", json={"name": "Strategy"})
    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["name"] == "strategy"

    list_response = client.get("/api/games/tags")
    assert list_response.status_code == 200
    tags = list_response.get_json()
    assert any(tag["id"] == created["id"] for tag in tags)
    assert any(tag["name"] == "strategy" for tag in tags)


def test_create_duplicate_tag_rejected(client):
    first = client.post("/api/games/tags", json={"name": "Family"})
    assert first.status_code == 201

    second = client.post("/api/games/tags", json={"name": " family "})
    assert second.status_code == 400
    assert second.get_json()["error"] == "Tag already exists"


def test_attach_and_list_tag_for_game(client):
    game_response = client.post(
        "/api/games/",
        json={
            "title": "Azul",
            "min_players": 2,
            "max_players": 4,
            "playtime_min": 45,
            "complexity": 2.0,
        },
    )
    game_id = game_response.get_json()["id"]

    tag_response = client.post("/api/games/tags", json={"name": "Abstract"})
    tag_id = tag_response.get_json()["id"]

    link_response = client.post(
        f"/api/games/{game_id}/tags",
        json={"tag_id": tag_id},
    )
    assert link_response.status_code == 201
    link = link_response.get_json()
    assert link["game_id"] == game_id
    assert link["game_tag_id"] == tag_id

    list_response = client.get(f"/api/games/{game_id}/tags")
    assert list_response.status_code == 200
    tags = list_response.get_json()
    assert any(tag["id"] == tag_id for tag in tags)


def test_attach_duplicate_tag_to_game_rejected(client):
    game_response = client.post(
        "/api/games/",
        json={
            "title": "Splendor",
            "min_players": 2,
            "max_players": 4,
            "playtime_min": 30,
            "complexity": 1.8,
        },
    )
    game_id = game_response.get_json()["id"]

    tag_response = client.post("/api/games/tags", json={"name": "Engine"})
    tag_id = tag_response.get_json()["id"]

    first_link = client.post(f"/api/games/{game_id}/tags", json={"tag_id": tag_id})
    assert first_link.status_code == 201

    second_link = client.post(f"/api/games/{game_id}/tags", json={"tag_id": tag_id})
    assert second_link.status_code == 400
    assert second_link.get_json()["error"] == "Tag is already linked to this game"


def test_remove_tag_from_game(client):
    game_response = client.post(
        "/api/games/",
        json={
            "title": "Wingspan",
            "min_players": 1,
            "max_players": 5,
            "playtime_min": 70,
            "complexity": 2.4,
        },
    )
    game_id = game_response.get_json()["id"]

    tag_response = client.post("/api/games/tags", json={"name": "Nature"})
    tag_id = tag_response.get_json()["id"]

    link_response = client.post(f"/api/games/{game_id}/tags", json={"tag_id": tag_id})
    assert link_response.status_code == 201

    delete_response = client.delete(f"/api/games/{game_id}/tags/{tag_id}")
    assert delete_response.status_code == 204

    list_response = client.get(f"/api/games/{game_id}/tags")
    assert list_response.status_code == 200
    assert list_response.get_json() == []
