from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _ensure_admin_user(app, email: str = "games-tag-edges-admin@example.com") -> str:
    with app.app_context():
        existing = UserDB.query.filter_by(email=email).first()
        if existing is None:
            db.session.add(
                UserDB(
                    role="admin",
                    name="Games Tag Edges Admin",
                    email=email,
                    password_hash=hash_password("password123"),
                )
            )
            db.session.commit()
    return email


def _login(client, email: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 200


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


def _create_tag(client, name: str = "strategy") -> int:
    response = client.post("/api/games/tags", json={"name": name})
    assert response.status_code == 201
    return response.get_json()["id"]


def test_paginated_games_include_tags(client, app):
    _login(client, _ensure_admin_user(app))

    game_id = _create_game(client, "Azul")
    tag_id = _create_tag(client, "Abstract")

    attach_response = client.post(f"/api/games/{game_id}/tags", json={"tag_id": tag_id})
    assert attach_response.status_code == 201

    response = client.get("/api/games/?page=1&page_size=10")
    assert response.status_code == 200
    payload = response.get_json()

    assert "games" in payload
    assert len(payload["games"]) >= 1

    azul = next((g for g in payload["games"] if g["id"] == game_id), None)
    assert azul is not None
    assert "tags" in azul
    assert any(tag["id"] == tag_id for tag in azul["tags"])


def test_tag_and_tags_query_params_match(client, app):
    _login(client, _ensure_admin_user(app))

    game_id = _create_game(client, "Wingspan")
    tag_id = _create_tag(client, "Nature")

    attach_response = client.post(f"/api/games/{game_id}/tags", json={"tag_id": tag_id})
    assert attach_response.status_code == 201

    by_tag = client.get("/api/games/?tag=nature")
    by_tags = client.get("/api/games/?tags=nature")

    assert by_tag.status_code == 200
    assert by_tags.status_code == 200

    payload_tag = by_tag.get_json()
    payload_tags = by_tags.get_json()

    assert payload_tag["total_count"] == payload_tags["total_count"]
    ids_tag = sorted(game["id"] for game in payload_tag["games"])
    ids_tags = sorted(game["id"] for game in payload_tags["games"])
    assert ids_tag == ids_tags


def test_removed_tag_not_present_in_game_response(client, app):
    _login(client, _ensure_admin_user(app))

    game_id = _create_game(client, "Terraforming Mars")
    tag_id = _create_tag(client, "Engine")

    attach_response = client.post(f"/api/games/{game_id}/tags", json={"tag_id": tag_id})
    assert attach_response.status_code == 201

    get_before = client.get(f"/api/games/{game_id}")
    assert get_before.status_code == 200
    before_tags = get_before.get_json()["tags"]
    assert any(tag["id"] == tag_id for tag in before_tags)

    remove_response = client.delete(f"/api/games/{game_id}/tags/{tag_id}")
    assert remove_response.status_code == 204

    get_after = client.get(f"/api/games/{game_id}")
    assert get_after.status_code == 200
    after_tags = get_after.get_json()["tags"]
    assert all(tag["id"] != tag_id for tag in after_tags)
