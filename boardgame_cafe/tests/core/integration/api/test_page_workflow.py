def test_homepage_shows_primary_ctas(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Book a Session" in body
    assert "See Our Game Library" in body


def test_games_page_is_public(client):
    response = client.get("/games")

    assert response.status_code == 200


def test_booking_page_redirects_to_login_when_unauthenticated(client):
    response = client.get("/booking")

    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert "/login" in location
    assert ("next=%2Fbooking" in location) or ("next=/booking" in location)


def test_login_page_contains_signup_prompt(client):
    response = client.get("/login")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Don't have an account? Sign up here!" in body


def test_booking_page_does_not_render_previous_bookings_table(app):
    from features.users.infrastructure import UserDB, hash_password
    from shared.infrastructure import db

    password = "BookingPagePwd123"
    with app.app_context():
        user = UserDB(
            name="Booking User",
            email="booking@example.com",
            password_hash=hash_password(password),
            role="customer",
        )
        db.session.add(user)
        db.session.commit()

    with app.test_client() as client:
        login_response = client.post(
            "/api/auth/login",
            data={"email": "booking@example.com", "password": password},
        )
        assert login_response.status_code in (200, 302)

        response = client.get("/booking")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "id=\"reservations-table\"" not in body