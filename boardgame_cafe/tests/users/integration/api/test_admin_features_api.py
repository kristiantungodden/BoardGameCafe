from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _create_user(*, role: str, name: str, email: str, password: str, force_password_change: bool = False) -> int:
    user = UserDB(
        role=role,
        name=name,
        email=email,
        password_hash=hash_password(password),
        force_password_change=force_password_change,
    )
    db.session.add(user)
    db.session.commit()
    return int(user.id)


def _login(client, *, email: str, password: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200


def test_admin_can_create_steward_and_steward_is_forced_to_change_password(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Admin",
            email="admin-create-steward@example.com",
            password="AdminPass123",
        )

    _login(client, email="admin-create-steward@example.com", password="AdminPass123")

    create_response = client.post(
        "/api/admin/stewards",
        json={
            "name": "Steward One",
            "email": "steward-one@example.com",
            "password": "StewardTemp123",
            "phone": "55512345",
        },
    )

    assert create_response.status_code == 201
    created = create_response.get_json()
    assert created["role"] == "staff"
    assert created["force_password_change"] is True

    client.post("/api/auth/logout")

    login_steward = client.post(
        "/api/auth/login",
        json={"email": "steward-one@example.com", "password": "StewardTemp123"},
    )
    assert login_steward.status_code == 200
    assert login_steward.get_json()["requires_password_change"] is True

    blocked_me = client.get("/api/auth/me")
    assert blocked_me.status_code == 403
    assert blocked_me.get_json()["requires_password_change"] is True


def test_admin_can_list_users_and_force_password_reset(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Admin",
            email="admin-list@example.com",
            password="AdminPass123",
        )
        target_id = _create_user(
            role="customer",
            name="Target User",
            email="target-user@example.com",
            password="CustomerPass123",
            force_password_change=False,
        )

    _login(client, email="admin-list@example.com", password="AdminPass123")

    list_response = client.get("/api/admin/users")
    assert list_response.status_code == 200
    users = list_response.get_json()
    assert any(u["email"] == "target-user@example.com" for u in users)

    reset_response = client.post(f"/api/admin/users/{target_id}/force-password-reset")
    assert reset_response.status_code == 200
    reset_payload = reset_response.get_json()
    assert reset_payload["force_password_change"] is True


def test_non_admin_cannot_access_admin_user_management(app, client):
    with app.app_context():
        _create_user(
            role="staff",
            name="Staff",
            email="staff-no-admin@example.com",
            password="StaffPass123",
        )

    _login(client, email="staff-no-admin@example.com", password="StaffPass123")

    response = client.get("/api/admin/users")
    assert response.status_code == 403
    assert response.get_json()["error"] == "Admin access required"


def test_forced_password_user_can_change_password_without_current_password(app, client):
    with app.app_context():
        _create_user(
            role="staff",
            name="Forced User",
            email="forced-user@example.com",
            password="OldPass123",
            force_password_change=True,
        )

    _login(client, email="forced-user@example.com", password="OldPass123")

    change_response = client.post(
        "/api/auth/change-password",
        json={"new_password": "NewPass123"},
    )
    assert change_response.status_code == 200

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200

    client.post("/api/auth/logout")
    relogin = client.post(
        "/api/auth/login",
        json={"email": "forced-user@example.com", "password": "NewPass123"},
    )
    assert relogin.status_code == 200


def test_non_forced_user_must_send_current_password_to_change_password(app, client):
    with app.app_context():
        _create_user(
            role="customer",
            name="Normal User",
            email="normal-user@example.com",
            password="NormalPass123",
            force_password_change=False,
        )

    _login(client, email="normal-user@example.com", password="NormalPass123")

    missing_current = client.post(
        "/api/auth/change-password",
        json={"new_password": "UpdatedPass123"},
    )
    assert missing_current.status_code == 400
    assert missing_current.get_json()["error"] == "current_password is required"

    wrong_current = client.post(
        "/api/auth/change-password",
        json={"current_password": "WrongPass123", "new_password": "UpdatedPass123"},
    )
    assert wrong_current.status_code == 400
    assert wrong_current.get_json()["error"] == "Current password is incorrect"

    ok_change = client.post(
        "/api/auth/change-password",
        json={"current_password": "NormalPass123", "new_password": "UpdatedPass123"},
    )
    assert ok_change.status_code == 200
