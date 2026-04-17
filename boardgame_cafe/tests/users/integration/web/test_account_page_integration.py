"""Integration tests for the /me account page."""


def _create_and_login_user(client, *, name, email, password_hash, role="customer", phone=None):
    from features.users.infrastructure import UserDB, hash_password
    from shared.infrastructure import db

    with client.application.app_context():
        user = UserDB(
            name=name,
            email=email,
            password_hash=hash_password(password_hash),
            role=role,
            phone=phone,
        )
        db.session.add(user)
        db.session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password_hash,
        },
    )

    assert login_response.status_code == 200


def test_account_page_updates_profile(client):
    """The account page should allow a customer to update their profile."""
    from features.users.infrastructure import UserDB
    from shared.infrastructure import db

    _create_and_login_user(
        client,
        name="Test User",
        email="customer@example.com",
        password_hash="SecurePassword123",
        phone="555-1234",
    )

    response = client.get("/me")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Edit profile" in html
    assert "profile-view-grid" in html
    assert "profile-form" in html
    assert "name=\"name\"" in html
    assert 'readonly' in html
    assert "Account summary" not in html

    response = client.post(
        "/me",
        data={
            "csrf_token": "test-token",
            "name": "Updated User",
            "phone": "555-5678",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Updated User" in html
    assert "555-5678" in html

    with client.application.app_context():
        user = db.session.query(UserDB).filter_by(email="customer@example.com").first()
        assert user.name == "Updated User"
        assert user.phone == "555-5678"


def test_account_page_shows_role_for_staff(client):
    """Staff and admin users should see their elevated access level."""
    _create_and_login_user(
        client,
        name="Staff User",
        email="staff@example.com",
        password_hash="SecurePassword123",
        role="staff",
    )

    response = client.get("/me")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Staff access" in html
    assert "Role" in html