from datetime import datetime, timedelta, timezone

from features.users.infrastructure import UserDB, hash_password
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.incident_db import IncidentDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.announcement_db import AnnouncementDB
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

    client.post("/api/auth/logout")
    _login(client, email="target-user@example.com", password="CustomerPass123")

    same_password_change = client.post(
        "/api/auth/change-password",
        json={"new_password": "CustomerPass123"},
    )
    assert same_password_change.status_code == 400
    assert same_password_change.get_json()["error"] == "New password must be different from current password"

    valid_change = client.post(
        "/api/auth/change-password",
        json={"new_password": "CustomerPass456"},
    )
    assert valid_change.status_code == 200


def test_admin_can_suspend_user_but_not_self(app, client):
    with app.app_context():
        admin_id = _create_user(
            role="admin",
            name="Admin",
            email="admin-suspend@example.com",
            password="AdminPass123",
        )
        target_id = _create_user(
            role="customer",
            name="Suspend Target",
            email="suspend-target@example.com",
            password="CustomerPass123",
        )

    _login(client, email="admin-suspend@example.com", password="AdminPass123")

    suspend_target = client.patch(
        f"/api/admin/users/{target_id}/suspension",
        json={"suspended": True},
    )
    assert suspend_target.status_code == 200
    assert suspend_target.get_json()["is_suspended"] is True

    users_after_suspend = client.get("/api/admin/users")
    assert users_after_suspend.status_code == 200
    suspended_user = next((u for u in users_after_suspend.get_json() if u["id"] == target_id), None)
    assert suspended_user is not None
    assert suspended_user["is_suspended"] is True

    client.post("/api/auth/logout")

    suspended_login = client.post(
        "/api/auth/login",
        json={"email": "suspend-target@example.com", "password": "CustomerPass123"},
    )
    assert suspended_login.status_code == 403
    assert suspended_login.get_json()["error"] == "Account suspended"

    _login(client, email="admin-suspend@example.com", password="AdminPass123")

    suspend_self = client.patch(
        f"/api/admin/users/{admin_id}/suspension",
        json={"suspended": True},
    )
    assert suspend_self.status_code == 400
    assert suspend_self.get_json()["error"] == "You cannot suspend your own account."


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


def test_admin_cannot_suspend_last_active_admin(app, client):
    with app.app_context():
        admin_id = _create_user(
            role="admin",
            name="Solo Admin",
            email="solo-admin@example.com",
            password="AdminPass123",
        )

    _login(client, email="solo-admin@example.com", password="AdminPass123")

    suspend_self_admin = client.patch(
        f"/api/admin/users/{admin_id}/suspension",
        json={"suspended": True},
    )
    assert suspend_self_admin.status_code == 400
    assert suspend_self_admin.get_json()["error"] == "You cannot suspend your own account."


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


def test_admin_pricing_rejects_invalid_payloads_and_expired_timestamp(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Pricing Validation Admin",
            email="admin-pricing-validation@example.com",
            password="AdminPass123",
        )
        table = TableDB(table_nr="T77", capacity=2, floor=1, zone="main", status="available", price_cents=9000)
        game = GameDB(
            title="Brass Birmingham",
            min_players=2,
            max_players=4,
            playtime_min=120,
            complexity=3.9,
            price_cents=6500,
        )
        db.session.add(table)
        db.session.add(game)
        db.session.commit()
        table_id = int(table.id)
        game_id = int(game.id)

    _login(client, email="admin-pricing-validation@example.com", password="AdminPass123")

    negative_base_fee = client.put(
        "/api/admin/pricing/base-fee",
        json={"booking_base_fee_cents": -1},
    )
    assert negative_base_fee.status_code == 400

    expired_override = client.put(
        "/api/admin/pricing/base-fee",
        json={
            "booking_base_fee_cents": 2500,
            "booking_base_fee_active_until": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        },
    )
    assert expired_override.status_code == 400
    assert expired_override.get_json()["error"] == "booking_base_fee_active_until must be in the future"

    invalid_table_price = client.put(
        f"/api/admin/pricing/tables/{table_id}",
        json={"price_cents": "not-an-int"},
    )
    assert invalid_table_price.status_code == 400

    missing_game_price_field = client.put(
        f"/api/admin/pricing/games/{game_id}",
        json={},
    )
    assert missing_game_price_field.status_code == 400


def test_admin_can_manage_catalogue_and_copies(app, client):
    with app.app_context():
        _create_user(
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

    blocked_available = client.put(
        f"/api/admin/catalogue/copies/{copy_id}",
        json={"status": "available"},
    )
    assert blocked_available.status_code == 409
    assert blocked_available.get_json()["error"] == "Resolve incidents before setting copy to available."

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


def test_admin_catalogue_duplicate_copy_code_and_missing_entities(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Catalogue Validation Admin",
            email="admin-catalogue-validation@example.com",
            password="AdminPass123",
        )

    _login(client, email="admin-catalogue-validation@example.com", password="AdminPass123")

    create_game = client.post(
        "/api/admin/catalogue/games",
        json={
            "title": "Wingspan",
            "min_players": 1,
            "max_players": 5,
            "playtime_min": 70,
            "complexity": 2.5,
            "price_cents": 4200,
        },
    )
    assert create_game.status_code == 201
    game_id = create_game.get_json()["id"]

    first_copy = client.post(
        "/api/admin/catalogue/copies",
        json={
            "game_id": game_id,
            "copy_code": "WING-001",
            "status": "available",
        },
    )
    assert first_copy.status_code == 201
    copy_id = first_copy.get_json()["id"]

    duplicate_copy = client.post(
        "/api/admin/catalogue/copies",
        json={
            "game_id": game_id,
            "copy_code": "WING-001",
            "status": "available",
        },
    )
    assert duplicate_copy.status_code == 409

    missing_game_copy = client.post(
        "/api/admin/catalogue/copies",
        json={
            "game_id": 999999,
            "copy_code": "MISSING-001",
            "status": "available",
        },
    )
    assert missing_game_copy.status_code == 404

    missing_game_update = client.put(
        "/api/admin/catalogue/games/999999",
        json={"price_cents": 5000},
    )
    assert missing_game_update.status_code == 404

    missing_copy_update = client.put(
        "/api/admin/catalogue/copies/999999",
        json={"status": "maintenance"},
    )
    assert missing_copy_update.status_code == 404

    missing_copy_incidents = client.get("/api/admin/catalogue/copies/999999/incidents")
    assert missing_copy_incidents.status_code == 404

    missing_incident_resolve = client.post("/api/admin/catalogue/incidents/999999/resolve")
    assert missing_incident_resolve.status_code == 404

    delete_copy = client.delete(f"/api/admin/catalogue/copies/{copy_id}")
    assert delete_copy.status_code == 200


def test_admin_can_resolve_incident_and_restore_copy_to_available(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Incident Admin",
            email="admin-resolve-incident@example.com",
            password="AdminPass123",
        )
        staff_id = _create_user(
            role="staff",
            name="Incident Reporter",
            email="incident-reporter@example.com",
            password="StaffPass123",
        )
        game = GameDB(
            title="Catan",
            min_players=3,
            max_players=4,
            playtime_min=90,
            complexity=2.3,
            price_cents=3900,
            description="Trading and settlements",
            image_url=None,
        )
        db.session.add(game)
        db.session.commit()

        copy = GameCopyDB(
            game_id=game.id,
            copy_code="CATAN-001",
            status="maintenance",
            location="Repair shelf",
            condition_note="Missing road pieces",
        )
        db.session.add(copy)
        db.session.commit()

        incident = IncidentDB(
            game_copy_id=copy.id,
            reported_by=staff_id,
            incident_type="damage",
            note="Box corner crushed",
        )
        db.session.add(incident)
        db.session.commit()
        incident_id = int(incident.id)
        copy_id = int(copy.id)

    _login(client, email="admin-resolve-incident@example.com", password="AdminPass123")

    resolve_response = client.post(f"/api/admin/catalogue/incidents/{incident_id}/resolve")
    assert resolve_response.status_code == 200
    assert resolve_response.get_json()["copy"]["status"] == "available"

    incidents_response = client.get("/api/admin/catalogue/incidents")
    assert incidents_response.status_code == 200
    incidents = incidents_response.get_json()
    assert all(i["id"] != incident_id for i in incidents)

    with app.app_context():
        updated_copy = db.session.get(GameCopyDB, copy_id)
        assert updated_copy is not None
        assert updated_copy.status == "available"


def test_admin_cannot_set_copy_available_with_unresolved_incident(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Incident Gate Admin",
            email="admin-incident-gate@example.com",
            password="AdminPass123",
        )
        staff_id = _create_user(
            role="staff",
            name="Incident Reporter",
            email="incident-gate-reporter@example.com",
            password="StaffPass123",
        )
        game = GameDB(
            title="Ticket to Ride",
            min_players=2,
            max_players=5,
            playtime_min=60,
            complexity=2.1,
            price_cents=3500,
            description="Route-building game",
            image_url=None,
        )
        db.session.add(game)
        db.session.commit()

        copy = GameCopyDB(
            game_id=game.id,
            copy_code="TTR-001",
            status="maintenance",
            location="Repair shelf",
            condition_note="Needs review",
        )
        db.session.add(copy)
        db.session.commit()

        incident = IncidentDB(
            game_copy_id=copy.id,
            reported_by=staff_id,
            incident_type="damage",
            note="Damaged train cards",
        )
        db.session.add(incident)
        db.session.commit()
        copy_id = int(copy.id)
        incident_id = int(incident.id)

    _login(client, email="admin-incident-gate@example.com", password="AdminPass123")

    blocked = client.put(
        f"/api/admin/catalogue/copies/{copy_id}",
        json={"status": "available"},
    )
    assert blocked.status_code == 409
    assert blocked.get_json()["error"] == "Resolve incidents before setting copy to available."

    resolved = client.post(f"/api/admin/catalogue/incidents/{incident_id}/resolve")
    assert resolved.status_code == 200
    assert resolved.get_json()["copy"]["status"] == "available"


def test_admin_can_manage_announcements_and_home_shows_only_published(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Content Admin",
            email="admin-content@example.com",
            password="AdminPass123",
        )

    _login(client, email="admin-content@example.com", password="AdminPass123")

    create_draft = client.post(
        "/api/admin/content/announcements",
        json={
            "title": "Draft Promo",
            "body": "This draft should not show on the homepage.",
            "publish_now": False,
        },
    )
    assert create_draft.status_code == 201
    draft_id = create_draft.get_json()["id"]

    create_published = client.post(
        "/api/admin/content/announcements",
        json={
            "title": "Friday Event",
            "body": "Join our Friday board game night.",
            "cta_label": "Book now",
            "cta_url": "/booking",
            "publish_now": True,
        },
    )
    assert create_published.status_code == 201
    published_id = create_published.get_json()["id"]

    listing = client.get("/api/admin/content/announcements")
    assert listing.status_code == 200
    payload = listing.get_json()
    assert any(item["id"] == draft_id and item["is_published"] is False for item in payload)
    assert any(item["id"] == published_id and item["is_published"] is True for item in payload)

    publish_draft = client.post(f"/api/admin/content/announcements/{draft_id}/publish")
    assert publish_draft.status_code == 200
    assert publish_draft.get_json()["is_published"] is True

    unpublish_draft = client.post(f"/api/admin/content/announcements/{draft_id}/unpublish")
    assert unpublish_draft.status_code == 200
    assert unpublish_draft.get_json()["is_published"] is False

    home_response = client.get("/")
    assert home_response.status_code == 200
    html = home_response.get_data(as_text=True)
    assert "Friday Event" in html
    assert "Draft Promo" not in html

    delete_published = client.delete(f"/api/admin/content/announcements/{published_id}")
    assert delete_published.status_code == 200

    with app.app_context():
        assert db.session.get(AnnouncementDB, published_id) is None


def test_admin_can_edit_announcement(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Edit Admin",
            email="admin-edit-ann@example.com",
            password="AdminPass123",
        )

    _login(client, email="admin-edit-ann@example.com", password="AdminPass123")

    create = client.post(
        "/api/admin/content/announcements",
        json={"title": "Original Title", "body": "Original body text.", "publish_now": False},
    )
    assert create.status_code == 201
    ann_id = create.get_json()["id"]

    edit = client.put(
        f"/api/admin/content/announcements/{ann_id}",
        json={"title": "Updated Title", "body": "Updated body text."},
    )
    assert edit.status_code == 200
    updated = edit.get_json()
    assert updated["title"] == "Updated Title"
    assert updated["body"] == "Updated body text."
    assert updated["id"] == ann_id

    # Verify the change is persisted
    listing = client.get("/api/admin/content/announcements")
    items = listing.get_json()
    match = next(item for item in items if item["id"] == ann_id)
    assert match["title"] == "Updated Title"


def test_admin_announcement_validation_errors(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Announcement Validation Admin",
            email="admin-ann-validation@example.com",
            password="AdminPass123",
        )

    _login(client, email="admin-ann-validation@example.com", password="AdminPass123")

    blank_title = client.post(
        "/api/admin/content/announcements",
        json={"title": "   ", "body": "Valid body"},
    )
    assert blank_title.status_code == 400

    blank_body = client.post(
        "/api/admin/content/announcements",
        json={"title": "Valid title", "body": "   "},
    )
    assert blank_body.status_code == 400

    cta_pair_mismatch = client.post(
        "/api/admin/content/announcements",
        json={"title": "CTA mismatch", "body": "Missing URL", "cta_label": "Book now"},
    )
    assert cta_pair_mismatch.status_code == 400
    assert cta_pair_mismatch.get_json()["error"] == "cta_label and cta_url must either both be set or both be empty"

    invalid_cta_url = client.post(
        "/api/admin/content/announcements",
        json={
            "title": "Bad URL",
            "body": "Body",
            "cta_label": "Book",
            "cta_url": "javascript:alert(1)",
        },
    )
    assert invalid_cta_url.status_code == 400

    create = client.post(
        "/api/admin/content/announcements",
        json={"title": "Editable", "body": "Initial body"},
    )
    assert create.status_code == 201
    ann_id = create.get_json()["id"]

    blank_update_title = client.put(
        f"/api/admin/content/announcements/{ann_id}",
        json={"title": "   "},
    )
    assert blank_update_title.status_code == 400


def test_admin_announcement_lifecycle_transition_conflicts(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Lifecycle Admin",
            email="admin-lifecycle-ann@example.com",
            password="AdminPass123",
        )

    _login(client, email="admin-lifecycle-ann@example.com", password="AdminPass123")

    published = client.post(
        "/api/admin/content/announcements",
        json={"title": "Published", "body": "Already live", "publish_now": True},
    )
    assert published.status_code == 201
    published_id = published.get_json()["id"]

    draft = client.post(
        "/api/admin/content/announcements",
        json={"title": "Draft", "body": "Still draft", "publish_now": False},
    )
    assert draft.status_code == 201
    draft_id = draft.get_json()["id"]

    republish = client.post(f"/api/admin/content/announcements/{published_id}/publish")
    assert republish.status_code == 409
    assert republish.get_json()["error"] == "Announcement is already published"

    re_unpublish = client.post(f"/api/admin/content/announcements/{draft_id}/unpublish")
    assert re_unpublish.status_code == 409
    assert re_unpublish.get_json()["error"] == "Announcement is already unpublished"


def test_non_admin_cannot_access_catalogue_endpoints(app, client):
    with app.app_context():
        _create_user(
            role="customer",
            name="Customer",
            email="customer-catalogue@example.com",
            password="CustomerPass123",
        )

    _login(client, email="customer-catalogue@example.com", password="CustomerPass123")

    for method, path, body in [
        ("get", "/api/admin/catalogue", None),
        ("post", "/api/admin/catalogue/games", {"title": "X", "min_players": 1, "max_players": 4, "playtime_min": 30, "complexity": 1.0}),
        ("delete", "/api/admin/catalogue/games/1", None),
        ("get", "/api/admin/catalogue/incidents", None),
    ]:
        resp = getattr(client, method)(path, json=body)
        assert resp.status_code in (401, 403), f"Expected 401/403 for {method.upper()} {path}, got {resp.status_code}"


def test_admin_user_listing_rejects_invalid_role_filter(app, client):
    with app.app_context():
        _create_user(
            role="admin",
            name="Admin",
            email="admin-invalid-role-filter@example.com",
            password="AdminPass123",
        )

    _login(client, email="admin-invalid-role-filter@example.com", password="AdminPass123")

    response = client.get("/api/admin/users?role=superadmin")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Invalid role filter"


def test_non_admin_cannot_access_pricing_endpoints(app, client):
    with app.app_context():
        _create_user(
            role="customer",
            name="Customer",
            email="customer-pricing@example.com",
            password="CustomerPass123",
        )

    _login(client, email="customer-pricing@example.com", password="CustomerPass123")

    for method, path, body in [
        ("get", "/api/admin/pricing", None),
        ("put", "/api/admin/pricing/base-fee", {"booking_base_fee_cents": 500}),
    ]:
        resp = getattr(client, method)(path, json=body)
        assert resp.status_code in (401, 403), f"Expected 401/403 for {method.upper()} {path}, got {resp.status_code}"
