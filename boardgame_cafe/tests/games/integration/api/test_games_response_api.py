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