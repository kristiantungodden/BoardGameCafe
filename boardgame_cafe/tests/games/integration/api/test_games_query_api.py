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