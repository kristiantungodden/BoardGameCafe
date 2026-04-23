import pytest

import features.tables.presentation.api.admin_routes as admin_routes


@pytest.fixture(autouse=True)
def bypass_admin_auth(monkeypatch):
    monkeypatch.setattr(admin_routes, "_require_admin", lambda: None)


def _create_floor(client, number=1, name="Main Floor"):
    response = client.post(
        "/api/admin/floors",
        json={"number": number, "name": name, "active": True, "notes": None},
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


def _create_zone(client, floor=1, name="Zone A"):
    response = client.post(
        "/api/admin/zones",
        json={"floor": floor, "name": name, "active": True, "notes": None},
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


def _create_table(client, number=10, floor=1, zone="Zone A"):
    response = client.post(
        "/api/admin/tables",
        json={
            "number": number,
            "capacity": 4,
            "floor": floor,
            "zone": zone,
            "status": "available",
            "features": {},
        },
    )
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


def test_admin_zone_rename_propagates_to_assigned_tables(client):
    _create_floor(client, number=1)
    zone = _create_zone(client, floor=1, name="Corner")
    table = _create_table(client, number=12, floor=1, zone="Corner")

    update_response = client.patch(
        f"/api/admin/zones/{zone['id']}",
        json={"floor": 1, "name": "Patio", "active": True, "notes": None},
    )
    assert update_response.status_code == 200, update_response.get_data(as_text=True)

    list_tables = client.get("/api/admin/tables?floor=1")
    assert list_tables.status_code == 200
    tables = list_tables.get_json()
    updated_table = next((item for item in tables if item["id"] == table["id"]), None)
    assert updated_table is not None
    assert updated_table["zone"] == "Patio"


def test_admin_zone_delete_requires_force_when_tables_assigned(client):
    _create_floor(client, number=1)
    zone = _create_zone(client, floor=1, name="Zone B")
    _create_table(client, number=22, floor=1, zone="Zone B")

    delete_response = client.delete(f"/api/admin/zones/{zone['id']}")
    assert delete_response.status_code == 400
    assert "Cannot delete zone with tables assigned" in delete_response.get_json()["error"]


def test_admin_zone_force_delete_removes_zone_and_tables(client):
    _create_floor(client, number=1)
    zone = _create_zone(client, floor=1, name="Zone C")
    table = _create_table(client, number=23, floor=1, zone="Zone C")

    delete_response = client.delete(f"/api/admin/zones/{zone['id']}?force=1")
    assert delete_response.status_code == 204

    zones_response = client.get("/api/admin/zones?floor=1")
    assert zones_response.status_code == 200
    zone_ids = {item["id"] for item in zones_response.get_json()}
    assert zone["id"] not in zone_ids

    tables_response = client.get("/api/admin/tables?floor=1")
    assert tables_response.status_code == 200
    table_ids = {item["id"] for item in tables_response.get_json()}
    assert table["id"] not in table_ids


def test_admin_floor_force_delete_removes_floor_zones_and_tables(client):
    floor = _create_floor(client, number=2, name="Upstairs")
    _create_zone(client, floor=2, name="North")
    _create_table(client, number=32, floor=2, zone="North")

    delete_response = client.delete(f"/api/admin/floors/{floor['id']}")
    assert delete_response.status_code == 400
    assert "Cannot delete floor with tables assigned to it" in delete_response.get_json()["error"]

    force_delete = client.delete(f"/api/admin/floors/{floor['id']}?force=1")
    assert force_delete.status_code == 204

    floors_response = client.get("/api/admin/floors")
    assert floors_response.status_code == 200
    floor_ids = {item["id"] for item in floors_response.get_json()}
    assert floor["id"] not in floor_ids

    zones_response = client.get("/api/admin/zones?floor=2")
    assert zones_response.status_code == 200
    assert zones_response.get_json() == []

    tables_response = client.get("/api/admin/tables?floor=2")
    assert tables_response.status_code == 200
    assert tables_response.get_json() == []


def test_admin_table_can_move_between_zone_and_floor(client):
    _create_floor(client, number=1, name="Main")
    _create_zone(client, floor=1, name="A")

    _create_floor(client, number=2, name="Second")
    _create_zone(client, floor=2, name="B")

    table = _create_table(client, number=40, floor=1, zone="A")

    move_response = client.patch(
        f"/api/admin/tables/{table['id']}",
        json={
            "number": table["number"],
            "capacity": table["capacity"],
            "floor": 2,
            "zone": "B",
            "status": table["status"],
            "features": table["features"],
            "width": table["width"],
            "height": table["height"],
            "rotation": table["rotation"],
        },
    )
    assert move_response.status_code == 200, move_response.get_data(as_text=True)
    moved_table = move_response.get_json()
    assert moved_table["floor"] == 2
    assert moved_table["zone"] == "B"

    tables_floor_1 = client.get("/api/admin/tables?floor=1")
    assert tables_floor_1.status_code == 200
    assert table["id"] not in {row["id"] for row in tables_floor_1.get_json()}

    tables_floor_2 = client.get("/api/admin/tables?floor=2")
    assert tables_floor_2.status_code == 200
    moved = next((row for row in tables_floor_2.get_json() if row["id"] == table["id"]), None)
    assert moved is not None
    assert moved["zone"] == "B"


def test_admin_table_move_rejects_unknown_target_zone(client):
    _create_floor(client, number=1, name="Main")
    _create_zone(client, floor=1, name="A")

    _create_floor(client, number=2, name="Second")
    table = _create_table(client, number=41, floor=1, zone="A")

    move_response = client.patch(
        f"/api/admin/tables/{table['id']}",
        json={
            "number": table["number"],
            "capacity": table["capacity"],
            "floor": 2,
            "zone": "Missing Zone",
            "status": table["status"],
            "features": table["features"],
            "width": table["width"],
            "height": table["height"],
            "rotation": table["rotation"],
        },
    )
    assert move_response.status_code == 400
    assert "Zone not found for selected floor" in move_response.get_json()["error"]
