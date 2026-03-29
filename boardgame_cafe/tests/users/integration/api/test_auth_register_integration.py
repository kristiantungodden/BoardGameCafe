"""Integration tests for /auth/register.

These tests should use the Flask app fixture and real dependency wiring.
"""

def test_register_persists_user_and_returns_201(client):
    """Test registering a new user persists to database and returns 201."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "password": "SecurePassword123",
            "phone": "555-1234",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "User registered successfully"

    # Verify user was saved to database
    from features.users.infrastructure import UserDB
    from shared.infrastructure import db

    with client.application.app_context():
        user = db.session.query(UserDB).filter_by(email="alice@example.com").first()
        assert user is not None
        assert user.name == "Alice Johnson"
        assert user.email == "alice@example.com"
        assert user.phone == "555-1234"
        assert user.role == "customer"


def test_register_returns_409_for_duplicate_email(client):
    """Test registering with duplicate email returns 409."""
    from features.users.infrastructure import UserDB, hash_password
    from shared.infrastructure import db

    # Create an existing user
    with client.application.app_context():
        existing_user = UserDB(
            name="Existing User",
            email="existing@example.com",
            password_hash=hash_password("Password123"),
            role="customer",
        )
        db.session.add(existing_user)
        db.session.commit()

    # Try to register with the same email
    response = client.post(
        "/auth/register",
        json={
            "name": "New User",
            "email": "existing@example.com",
            "password": "SecurePassword123",
        },
    )

    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "email already exists"


def test_register_returns_400_for_invalid_payload(client):
    """Test register returns 400 for invalid/missing payload."""
    # Missing email
    response = client.post(
        "/auth/register",
        json={
            "name": "John Doe",
            "password": "SecurePassword123",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Registration failed"
    assert "details" in data

    # Invalid email format
    response = client.post(
        "/auth/register",
        json={
            "name": "John Doe",
            "email": "invalid-email",
            "password": "SecurePassword123",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Registration failed"

    # Password too short
    response = client.post(
        "/auth/register",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "Short1",  # Less than 8 characters
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Registration failed"


def test_register_with_valid_role(client):
    """Test registering with a valid role."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Staff Member",
            "email": "staff@example.com",
            "password": "SecurePassword123",
            "role": "staff",
        },
    )

    assert response.status_code == 201

    # Verify the role was saved
    from features.users.infrastructure import UserDB
    from shared.infrastructure import db

    with client.application.app_context():
        user = db.session.query(UserDB).filter_by(email="staff@example.com").first()
        assert user.role == "staff"


def test_register_defaults_role_to_customer(client):
    """Test that registration defaults role to customer."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Customer User",
            "email": "customer@example.com",
            "password": "SecurePassword123",
        },
    )

    assert response.status_code == 201

    # Verify the role defaults to customer
    from features.users.infrastructure import UserDB
    from shared.infrastructure import db

    with client.application.app_context():
        user = db.session.query(UserDB).filter_by(email="customer@example.com").first()
        assert user.role == "customer"
