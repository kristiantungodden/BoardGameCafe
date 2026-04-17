from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _login_as_admin(client, app):
    with app.app_context():
        existing = UserDB.query.filter_by(email="games-response-admin@example.com").first()
        if existing is None:
            db.session.add(
                UserDB(
                    role="admin",
                    name="Games Response Admin",
                    email="games-response-admin@example.com",
                    password_hash=hash_password("password123"),
                )
            )
            db.session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"email": "games-response-admin@example.com", "password": "password123"},
    )
    assert login_response.status_code == 200


def test_get_games_returns_tags_in_response(client):
    response = client.post(
        "/api/games/",
        json={
            "title": "Catan",
            "min_players": 3,
            "max_players": 4,
            "playtime_min": 60,
            "complexity": 2.5,
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert "tags" in data
    assert isinstance(data["tags"], list)

    response = client.get("/api/games/")
    assert response.status_code == 200
    games = response.get_json()
    for game in games:
        assert "tags" in game


def test_get_and_update_game_expose_attached_tags(client, app):
    _login_as_admin(client, app)

    create_game = client.post(
        "/api/games/",
        json={
            "title": "Ticket to Ride",
            "min_players": 2,
            "max_players": 5,
            "playtime_min": 60,
            "complexity": 2.1,
        },
    )
    assert create_game.status_code == 201
    game_id = create_game.get_json()["id"]

    create_tag = client.post("/api/games/tags", json={"name": "Family"})
    assert create_tag.status_code == 201
    tag = create_tag.get_json()

    attach = client.post(f"/api/games/{game_id}/tags", json={"tag_id": tag["id"]})
    assert attach.status_code == 201

    get_response = client.get(f"/api/games/{game_id}")
    assert get_response.status_code == 200
    game_data = get_response.get_json()
    assert "tags" in game_data
    assert any(t["id"] == tag["id"] for t in game_data["tags"])

    update_response = client.put(
        f"/api/games/{game_id}",
        json={"title": "Ticket to Ride Europe"},
    )
    assert update_response.status_code == 200
    updated_data = update_response.get_json()
    assert "tags" in updated_data
    assert any(t["id"] == tag["id"] for t in updated_data["tags"])


def test_games_default_list_backward_compatible(client):
    client.post(
        "/api/games/",
        json={
            "title": "Catan",
            "min_players": 3,
            "max_players": 4,
            "playtime_min": 60,
            "complexity": 2.5,
        },
    )
    client.post(
        "/api/games/",
        json={
            "title": "Monopoly",
            "min_players": 2,
            "max_players": 6,
            "playtime_min": 90,
            "complexity": 1.5,
        },
    )

    response = client.get("/api/games/")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert all("title" in g for g in data)
    assert all("tags" in g for g in data)