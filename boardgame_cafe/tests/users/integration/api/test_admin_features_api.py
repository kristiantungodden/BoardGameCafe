from datetime import datetime, timedelta, timezone

from features.users.infrastructure import UserDB, hash_password
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.incident_db import IncidentDB
from features.tables.infrastructure.database.table_db import TableDB
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


def test_admin_can_get_and_update_pricing(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Pricing Admin",
            email="admin-pricing@example.com",
            password="AdminPass123",
        )
        table = TableDB(table_nr="T99", capacity=4, floor=1, zone="main", status="available", price_cents=15000)
        game = GameDB(
            title="Terraforming Mars",
            min_players=1,
            max_players=5,
            playtime_min=120,
            complexity=3.5,
            price_cents=5000,
        )
        db.session.add(table)
        db.session.add(game)
        db.session.commit()
        table_id = int(table.id)
        game_id = int(game.id)

    _login(client, email="admin-pricing@example.com", password="AdminPass123")

    get_response = client.get("/api/admin/pricing")
    assert get_response.status_code == 200
    payload = get_response.get_json()
    assert "booking_base_fee_cents" in payload
    assert "booking_cancel_time_limit_hours" in payload
    assert any(item["id"] == table_id for item in payload["tables"])
    assert any(item["id"] == game_id for item in payload["games"])

    active_until = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    base_response = client.put(
        "/api/admin/pricing/base-fee",
        json={
            "booking_base_fee_cents": 4900,
            "booking_base_fee_active_until": active_until,
            "booking_cancel_time_limit_hours": 24,
        },
    )
    table_response = client.put(f"/api/admin/pricing/tables/{table_id}", json={"price_cents": 22000})
    game_response = client.put(f"/api/admin/pricing/games/{game_id}", json={"price_cents": 7900})

    assert base_response.status_code == 200
    assert table_response.status_code == 200
    assert game_response.status_code == 200

    refreshed = client.get("/api/admin/pricing").get_json()
    assert refreshed["booking_base_fee_cents"] == 4900
    assert refreshed["booking_base_fee_default_cents"] == 2500
    assert refreshed["booking_base_fee_has_temporary_override"] is True
    assert refreshed["booking_base_fee_active_until"] is not None
    assert refreshed["booking_cancel_time_limit_hours"] == 24
    assert next(item for item in refreshed["tables"] if item["id"] == table_id)["price_cents"] == 22000
    assert next(item for item in refreshed["games"] if item["id"] == game_id)["price_cents"] == 7900

    permanent_response = client.put(
        "/api/admin/pricing/base-fee",
        json={
            "booking_base_fee_cents": 3600,
            "booking_base_fee_priority": 50,
            "booking_cancel_time_limit_hours": 12,
        },
    )
    assert permanent_response.status_code == 200

    refreshed_after_permanent = client.get("/api/admin/pricing").get_json()
    assert refreshed_after_permanent["booking_base_fee_cents"] == 3600
    assert refreshed_after_permanent["booking_base_fee_default_cents"] == 3600
    assert refreshed_after_permanent["booking_base_fee_has_temporary_override"] is False
    assert refreshed_after_permanent["booking_base_fee_active_until"] is None
    assert refreshed_after_permanent["booking_cancel_time_limit_hours"] == 12

    lower_priority_until = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    low_priority_override = client.put(
        "/api/admin/pricing/base-fee",
        json={
            "booking_base_fee_cents": 1500,
            "booking_base_fee_active_until": lower_priority_until,
            "booking_base_fee_priority": 0,
            "booking_cancel_time_limit_hours": 12,
        },
    )
    assert low_priority_override.status_code == 200

    after_low_priority_override = client.get("/api/admin/pricing").get_json()
    assert after_low_priority_override["booking_base_fee_default_cents"] == 3600
    assert after_low_priority_override["booking_base_fee_cents"] == 3600
    assert after_low_priority_override["booking_base_fee_default_priority"] == 50

    high_priority_override = client.put(
        "/api/admin/pricing/base-fee",
        json={
            "booking_base_fee_cents": 1500,
            "booking_base_fee_active_until": lower_priority_until,
            "booking_base_fee_priority": 100,
            "booking_cancel_time_limit_hours": 12,
        },
    )
    assert high_priority_override.status_code == 200

    after_high_priority_override = client.get("/api/admin/pricing").get_json()
    assert after_high_priority_override["booking_base_fee_default_cents"] == 3600
    assert after_high_priority_override["booking_base_fee_cents"] == 1500
    assert after_high_priority_override["booking_base_fee_has_temporary_override"] is True


def test_admin_can_manage_catalogue_and_copies(app, client):
    with app.app_context():
        admin_id = _create_user(
            role="admin",
            name="Catalogue Admin",
            email="admin-catalogue@example.com",
            password="AdminPass123",
        )
        staff_id = _create_user(
            role="staff",
            name="Steward Reporter",
            email="steward-reporter@example.com",
            password="StaffPass123",
        )

    _login(client, email="admin-catalogue@example.com", password="AdminPass123")

    create_game = client.post(
        "/api/admin/catalogue/games",
        json={
            "title": "Azul",
            "min_players": 2,
            "max_players": 4,
            "playtime_min": 45,
            "complexity": 2.0,
            "price_cents": 3500,
            "description": "Tile drafting game",
            "image_url": "https://example.com/azul.png",
        },
    )
    assert create_game.status_code == 201
    game_id = create_game.get_json()["id"]

    update_game = client.put(
        f"/api/admin/catalogue/games/{game_id}",
        json={"price_cents": 4200, "playtime_min": 50},
    )
    assert update_game.status_code == 200
    assert update_game.get_json()["price_cents"] == 4200

    create_copy = client.post(
        "/api/admin/catalogue/copies",
        json={
            "game_id": game_id,
            "copy_code": "AZUL-001",
            "status": "available",
            "location": "Shelf A",
            "condition_note": "Excellent",
        },
    )
    assert create_copy.status_code == 201
    copy_id = create_copy.get_json()["id"]

    update_copy = client.put(
        f"/api/admin/catalogue/copies/{copy_id}",
        json={"status": "maintenance", "location": "Back room"},
    )
    assert update_copy.status_code == 200
    assert update_copy.get_json()["status"] == "maintenance"

    with app.app_context():
        incident = IncidentDB(
            game_copy_id=copy_id,
            reported_by=staff_id,
            incident_type="damage",
            note="Corner wear",
        )
        db.session.add(incident)
        db.session.commit()

    incidents_resp = client.get(f"/api/admin/catalogue/copies/{copy_id}/incidents")
    assert incidents_resp.status_code == 200
    incidents = incidents_resp.get_json()
    assert any(i["incident_type"] == "damage" for i in incidents)

    overview = client.get("/api/admin/catalogue")
    assert overview.status_code == 200
    payload = overview.get_json()
    assert any(g["id"] == game_id for g in payload["games"])
    assert any(c["id"] == copy_id for c in payload["copies"])

    delete_game_before_copy = client.delete(f"/api/admin/catalogue/games/{game_id}")
    assert delete_game_before_copy.status_code == 409

    delete_copy = client.delete(f"/api/admin/catalogue/copies/{copy_id}")
    assert delete_copy.status_code == 200

    delete_game = client.delete(f"/api/admin/catalogue/games/{game_id}")
    assert delete_game.status_code == 200
