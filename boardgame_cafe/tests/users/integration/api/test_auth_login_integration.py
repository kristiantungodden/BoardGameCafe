"""Integration tests for /api/auth/login.

These tests should use the Flask app fixture and real dependency wiring.
"""


def test_login_returns_200_for_valid_credentials(client):
    """Test login with valid credentials returns 200 and user info."""
    from features.users.infrastructure import UserDB, hash_password
    from shared.infrastructure import db

    # Create a test user
    test_password = "TestPassword123"
    with client.application.app_context():
        user = UserDB(
            name="Test User",
            email="test@example.com",
            password_hash=hash_password(test_password),
            role="customer",
            phone="555-1234",
        )
        db.session.add(user)
        db.session.commit()

    # Login with valid credentials
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": test_password,
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Logged in"
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["name"] == "Test User"
    assert data["user"]["phone"] == "555-1234"
    assert data["user"]["role"] == "customer"
    assert "id" in data["user"]


def test_login_returns_401_for_invalid_credentials(client):
    """Test login with invalid credentials returns 401."""
    from features.users.infrastructure import UserDB, hash_password
    from shared.infrastructure import db

    # Create a test user
    with client.application.app_context():
        user = UserDB(
            name="Test User",
            email="test@example.com",
            password_hash=hash_password("CorrectPassword123"),
            role="customer",
        )
        db.session.add(user)
        db.session.commit()

    # Try login with wrong password
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Invalid credentials"

    # Try login with non-existent user
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123",
        },
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Invalid credentials"


def test_login_then_me_returns_current_user(client):
    """Test that after login, /me endpoint returns the logged-in user."""
    from features.users.infrastructure import UserDB, hash_password
    from shared.infrastructure import db

    # Create a test user
    test_password = "TestPassword123"
    with client.application.app_context():
        user = UserDB(
            name="Test User",
            email="test@example.com",
            password_hash=hash_password(test_password),
            role="customer",
            phone="555-9999",
        )
        db.session.add(user)
        db.session.commit()

    # Login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": test_password,
        },
    )

    assert login_response.status_code == 200

    # Now access the /me endpoint
    me_response = client.get("/api/auth/me")

    assert me_response.status_code == 200
    data = me_response.get_json()
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["name"] == "Test User"
    assert data["user"]["phone"] == "555-9999"


def test_login_returns_400_for_invalid_json(client):
    """Test login returns 400 for invalid JSON."""
    response = client.post(
        "/api/auth/login",
        data="invalid json {",
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Invalid JSON body"


def test_login_returns_400_for_missing_fields(client):
    """Test login returns 400 when required fields are missing."""
    # Missing password
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Validation failed"
    assert "details" in data

    # Missing email
    response = client.post(
        "/api/auth/login",
        json={
            "password": "TestPassword123",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Validation failed"
    assert "details" in data


def test_logout_removes_session(client):
    """Test that logout properly removes the session."""
    from features.users.infrastructure import UserDB, hash_password
    from shared.infrastructure import db

    # Create and login a test user
    test_password = "TestPassword123"
    with client.application.app_context():
        user = UserDB(
            name="Test User",
            email="test@example.com",
            password_hash=hash_password(test_password),
            role="customer",
        )
        db.session.add(user)
        db.session.commit()

    # Login
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": test_password,
        },
    )

    assert login_response.status_code == 200

    # Access /me to verify logged in
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200

    # Logout
    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    data = logout_response.get_json()
    assert data["message"] == "Logged out"

    # Try to access /me again - should fail
    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 401
