def test_homepage_shows_primary_ctas(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Book a Session" in body
    assert "See Our Game Library" in body


def test_games_page_is_public(client):
    response = client.get("/games")

    assert response.status_code == 200


def test_reservations_page_redirects_to_login_when_unauthenticated(client):
    response = client.get("/reservations")

    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert "/login" in location
    assert ("next=%2Freservations" in location) or ("next=/reservations" in location)


def test_login_page_contains_signup_prompt(client):
    response = client.get("/login")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Don't have an account? Sign up here!" in body