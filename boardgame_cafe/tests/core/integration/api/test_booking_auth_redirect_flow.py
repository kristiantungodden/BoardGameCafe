from datetime import datetime, timedelta


def test_auth_redirect_to_booking_then_confirmation_and_my_bookings(client, test_data):
    from features.users.infrastructure import UserDB, hash_password
    from shared.infrastructure import db

    password = "FlowPassword123"
    with client.application.app_context():
        user = UserDB(
            name="Flow User",
            email="flow@example.com",
            password_hash=hash_password(password),
            role="customer",
        )
        db.session.add(user)
        db.session.commit()

    redirect_response = client.get("/booking")
    assert redirect_response.status_code == 302
    location = redirect_response.headers.get("Location", "")
    assert "/login" in location
    assert ("next=%2Fbooking" in location) or ("next=/booking" in location)

    login_response = client.post(
        "/api/auth/login",
        data={
            "email": "flow@example.com",
            "password": password,
            "next": "/booking",
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 302
    assert login_response.headers.get("Location", "") == "/booking"

    now = datetime(2026, 4, 20, 18, 0)
    booking_response = client.post(
        "/api/reservations",
        json={
            "table_id": test_data["tables"][0]["id"],
            "table_ids": [test_data["tables"][0]["id"]],
            "start_ts": now.isoformat(),
            "end_ts": (now + timedelta(hours=2)).isoformat(),
            "party_size": 2,
            "games": [],
        },
    )
    assert booking_response.status_code == 201
    booking_body = booking_response.get_json()
    reservation_id = booking_body["id"]

    confirmation_response = client.get(f"/reservations/confirmation/{reservation_id}")
    assert confirmation_response.status_code == 200
    assert "Booking Confirmed" in confirmation_response.get_data(as_text=True)

    my_bookings_response = client.get("/my-bookings", follow_redirects=True)
    assert my_bookings_response.status_code == 200
    body = my_bookings_response.get_data(as_text=True)
    assert "My Bookings" in body
    assert "Upcoming bookings" in body
    assert "Past bookings" in body
    assert "booking-details-overlay" in body
    assert 'id="booking-details-overlay" hidden' in body
    assert "View details" in body
    assert "Booking reference" in body

    list_response = client.get("/api/reservations")
    assert list_response.status_code == 200
    rows = list_response.get_json()
    assert not any(item["id"] == reservation_id for item in rows)
