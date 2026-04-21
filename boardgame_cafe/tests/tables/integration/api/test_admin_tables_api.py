from __future__ import annotations

from datetime import datetime, timedelta

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.tables.infrastructure.database import FloorDB, TableDB, ZoneDB
from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _create_admin(app, *, email: str = "admin-tables@example.com") -> int:
    with app.app_context():
        admin = UserDB(
            role="admin",
            name="Admin",
            email=email,
            password_hash=hash_password("AdminPass123"),
            force_password_change=False,
        )
        db.session.add(admin)
        db.session.commit()
        return admin.id


def _login(client, *, email: str) -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": "AdminPass123"})
    assert response.status_code == 200


def test_admin_can_create_floor_and_table(app, client):
    _create_admin(app)
    _login(client, email="admin-tables@example.com")

    floor_response = client.post(
        "/api/admin/floors",
        json={"number": 1, "name": "Ground floor", "width": 100, "height": 80},
    )
    assert floor_response.status_code == 201
    floor = floor_response.get_json()
    assert floor["number"] == 1

    zone_response = client.post(
        "/api/admin/zones",
        json={"floor": 1, "name": "A"},
    )
    assert zone_response.status_code == 201

    table_response = client.post(
        "/api/admin/tables",
        json={
            "number": 10,
            "capacity": 4,
            "floor": 1,
            "zone": "A",
            "width": 4,
            "height": 4,
            "rotation": 0,
        },
    )
    assert table_response.status_code == 201
    table = table_response.get_json()
    assert table["number"] == 10
    assert table["floor"] == 1
    assert table["zone"] == "A"

    list_response = client.get("/api/admin/tables")
    assert list_response.status_code == 200
    assert any(item["number"] == 10 for item in list_response.get_json())


def test_admin_cannot_delete_table_with_future_reservation(app, client):
    _create_admin(app, email="admin-delete-table@example.com")
    _login(client, email="admin-delete-table@example.com")

    client.post("/api/admin/floors", json={"number": 1, "name": "Ground floor"})
    client.post("/api/admin/zones", json={"floor": 1, "name": "A"})
    table_response = client.post(
        "/api/admin/tables",
        json={"number": 20, "capacity": 4, "floor": 1, "zone": "A"},
    )
    table_id = table_response.get_json()["id"]

    with app.app_context():
        customer = UserDB(
            role="customer",
            name="Customer",
            email="customer-table-delete@example.com",
            password_hash=hash_password("CustomerPass123"),
            force_password_change=False,
        )
        db.session.add(customer)
        db.session.flush()

        booking = BookingDB(
            customer_id=customer.id,
            start_ts=datetime.utcnow() + timedelta(days=1),
            end_ts=datetime.utcnow() + timedelta(days=1, hours=2),
            party_size=4,
            status="confirmed",
            notes=None,
        )
        db.session.add(booking)
        db.session.flush()
        db.session.add(TableReservationDB(booking_id=booking.id, table_id=table_id))
        db.session.commit()

    delete_response = client.delete(f"/api/admin/tables/{table_id}")
    assert delete_response.status_code == 400
    assert delete_response.get_json()["error"] == "Cannot delete table with future reservations"


def test_admin_can_delete_empty_floor(app, client):
    _create_admin(app, email="admin-delete-floor@example.com")
    _login(client, email="admin-delete-floor@example.com")

    create_floor = client.post("/api/admin/floors", json={"number": 9, "name": "Pop-up floor"})
    floor_id = create_floor.get_json()["id"]

    response = client.delete(f"/api/admin/floors/{floor_id}")
    assert response.status_code == 204

    with app.app_context():
        assert db.session.get(FloorDB, floor_id) is None


def test_admin_can_manage_zones(app, client):
    _create_admin(app, email="admin-zone@example.com")
    _login(client, email="admin-zone@example.com")

    client.post("/api/admin/floors", json={"number": 2, "name": "Top floor"})

    create_zone = client.post("/api/admin/zones", json={"floor": 2, "name": "Patio"})
    assert create_zone.status_code == 201
    zone_id = create_zone.get_json()["id"]

    update_zone = client.patch(
        f"/api/admin/zones/{zone_id}",
        json={"floor": 2, "name": "Patio Updated", "active": True, "notes": "Summer"},
    )
    assert update_zone.status_code == 200
    assert update_zone.get_json()["name"] == "Patio Updated"

    list_zones = client.get("/api/admin/zones?floor=2")
    assert list_zones.status_code == 200
    assert any(item["name"] == "Patio Updated" for item in list_zones.get_json())

    delete_zone = client.delete(f"/api/admin/zones/{zone_id}")
    assert delete_zone.status_code == 204

    with app.app_context():
        assert db.session.get(ZoneDB, zone_id) is None


def test_admin_cannot_delete_zone_with_assigned_tables(app, client):
    _create_admin(app, email="admin-zone-delete@example.com")
    _login(client, email="admin-zone-delete@example.com")

    client.post("/api/admin/floors", json={"number": 3, "name": "Main"})
    zone_response = client.post("/api/admin/zones", json={"floor": 3, "name": "A"})
    assert zone_response.status_code == 201
    zone_id = zone_response.get_json()["id"]

    client.post(
        "/api/admin/tables",
        json={"number": 33, "capacity": 4, "floor": 3, "zone": "A"},
    )

    delete_response = client.delete(f"/api/admin/zones/{zone_id}")
    assert delete_response.status_code == 400
    assert delete_response.get_json()["error"] == "Cannot delete zone with tables assigned to it"