from __future__ import annotations

from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _create_user(*, email: str, password: str, name: str = "Test User", role: str = "customer") -> int:
    user = UserDB(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return int(user.id)


def test_auth_register_login_and_me_flow(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "password": "SecurePassword123",
            "phone": "555-1234",
        },
    )

    assert response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "SecurePassword123"},
    )

    assert login_response.status_code == 200
    payload = login_response.get_json()
    assert payload["message"] == "Logged in"
    assert payload["user"]["email"] == "alice@example.com"

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.get_json()["user"]["email"] == "alice@example.com"


def test_auth_login_rejects_suspended_user(client):
    _create_user(email="suspended@example.com", password="Secret123", name="Suspended")

    with client.application.app_context():
        user = db.session.query(UserDB).filter_by(email="suspended@example.com").first()
        user.is_suspended = True
        db.session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "suspended@example.com", "password": "Secret123"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Account suspended"


def test_change_password_requires_current_password_unless_forced_reset(client):
    _create_user(email="changepass@example.com", password="OldPassword123", name="Changer")

    client.post(
        "/api/auth/login",
        json={"email": "changepass@example.com", "password": "OldPassword123"},
    )

    response = client.post(
        "/api/auth/change-password",
        json={"new_password": "NewPassword123"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "current_password is required"
