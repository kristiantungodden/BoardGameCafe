from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _ensure_admin_user(app, email: str = "games-query-admin@example.com") -> str:
    with app.app_context():
        existing = UserDB.query.filter_by(email=email).first()
        if existing is None:
            db.session.add(
                UserDB(
                    role="admin",
                    name="Games Query Admin",
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


def test_get_games_with_pagination(client):
    for i in range(15):
        client.post(
            "/api/games/",
            json={
                "title": f"Game {i}",
                "min_players": 2,
                "max_players": 4,
                "playtime_min": 60,
                "complexity": 2.0,
            },
        )

    response = client.get("/api/games/?page=1")
    assert response.status_code == 200
    data = response.get_json()
    assert "games" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_count" in data
    assert "total_pages" in data
    assert len(data["games"]) == 10
    assert data["total_count"] == 15
    assert data["total_pages"] == 2
    assert data["page"] == 1

    response = client.get("/api/games/?page=2&page_size=10")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["games"]) == 5
    assert data["page"] == 2


def test_get_games_with_page_size(client):
    for i in range(10):
        client.post(
            "/api/games/",
            json={
                "title": f"Game {i}",
                "min_players": 2,
                "max_players": 4,
                "playtime_min": 60,
                "complexity": 2.0,
            },
        )

    response = client.get("/api/games/?page=1&page_size=5")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["games"]) == 5
    assert data["page_size"] == 5
    assert data["total_pages"] == 2


def test_get_games_with_search_filter(client):
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
            "title": "Catan: Seafarers",
            "min_players": 3,
            "max_players": 4,
            "playtime_min": 75,
            "complexity": 2.8,
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

    response = client.get("/api/games/?search=catan")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_count"] == 2
    titles = [g["title"] for g in data["games"]]
    assert "Catan" in titles
    assert "Catan: Seafarers" in titles
    assert "Monopoly" not in titles


def test_get_games_with_min_players_filter(client):
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
            "title": "Chess",
            "min_players": 2,
            "max_players": 2,
            "playtime_min": 30,
            "complexity": 3.0,
        },
    )
    client.post(
        "/api/games/",
        json={
            "title": "Solitaire",
            "min_players": 1,
            "max_players": 1,
            "playtime_min": 20,
            "complexity": 1.0,
        },
    )

    response = client.get("/api/games/?min_players=2")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_count"] == 2
    titles = [g["title"] for g in data["games"]]
    assert "Catan" in titles
    assert "Chess" in titles
    assert "Solitaire" not in titles


def test_get_games_with_max_players_filter(client):
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
    client.post(
        "/api/games/",
        json={
            "title": "War",
            "min_players": 2,
            "max_players": 8,
            "playtime_min": 45,
            "complexity": 1.8,
        },
    )

    response = client.get("/api/games/?max_players=4")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_count"] == 1
    assert data["games"][0]["title"] == "Catan"


def test_get_games_with_complexity_filter(client):
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

    response = client.get("/api/games/?complexity=2.5")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_count"] == 1
    assert data["games"][0]["title"] == "Catan"


def test_get_games_with_multiple_filters(client):
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
            "title": "Catan: Seafarers",
            "min_players": 3,
            "max_players": 5,
            "playtime_min": 75,
            "complexity": 2.8,
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

    response = client.get("/api/games/?search=catan&min_players=3")
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_count"] == 2
    titles = [g["title"] for g in data["games"]]
    assert "Catan" in titles
    assert "Catan: Seafarers" in titles


def test_get_games_pagination_clamps_invalid_values(client):
    for i in range(3):
        client.post(
            "/api/games/",
            json={
                "title": f"Clamp {i}",
                "min_players": 2,
                "max_players": 4,
                "playtime_min": 60,
                "complexity": 2.0,
            },
        )

    response = client.get("/api/games/?page=0&page_size=0")
    assert response.status_code == 200
    data = response.get_json()

    assert data["page"] == 1
    assert data["page_size"] == 1
    assert data["total_count"] == 3
    assert len(data["games"]) == 1


def test_get_games_out_of_range_page_returns_empty_list(client):
    for i in range(5):
        client.post(
            "/api/games/",
            json={
                "title": f"Page {i}",
                "min_players": 2,
                "max_players": 4,
                "playtime_min": 45,
                "complexity": 1.5,
            },
        )

    response = client.get("/api/games/?page=3&page_size=3")
    assert response.status_code == 200
    data = response.get_json()

    assert data["page"] == 3
    assert data["page_size"] == 3
    assert data["total_count"] == 5
    assert data["total_pages"] == 2
    assert data["games"] == []


def test_get_games_prefers_tag_over_tags_when_both_provided(client, app):
    _login(client, _ensure_admin_user(app))

    catan = client.post(
        "/api/games/",
        json={
            "title": "Catan",
            "min_players": 3,
            "max_players": 4,
            "playtime_min": 60,
            "complexity": 2.5,
        },
    )
    azul = client.post(
        "/api/games/",
        json={
            "title": "Azul",
            "min_players": 2,
            "max_players": 4,
            "playtime_min": 45,
            "complexity": 1.9,
        },
    )
    catan_id = catan.get_json()["id"]
    azul_id = azul.get_json()["id"]

    strategy_tag = client.post("/api/games/tags", json={"name": "strategy"}).get_json()[
        "id"
    ]
    abstract_tag = client.post("/api/games/tags", json={"name": "abstract"}).get_json()[
        "id"
    ]

    client.post(f"/api/games/{catan_id}/tags", json={"tag_id": strategy_tag})
    client.post(f"/api/games/{azul_id}/tags", json={"tag_id": abstract_tag})

    response = client.get("/api/games/?tag=strategy&tags=abstract")
    assert response.status_code == 200
    data = response.get_json()

    titles = [game["title"] for game in data["games"]]
    assert "Catan" in titles
    assert "Azul" not in titles