from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _create_admin(app, *, email="admin@floor-tests.example.com", password="AdminPass123"):
    with app.app_context():
        user = UserDB(
            role="admin",
            name="Admin",
            email=email,
            password_hash=hash_password(password),
        )
        db.session.add(user)
        db.session.commit()


def _login(client, *, email="admin@floor-tests.example.com", password="AdminPass123"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Floors
# ---------------------------------------------------------------------------

def test_admin_can_create_and_list_floors(app, client):
    _create_admin(app)
    _login(client)

    create = client.post("/api/admin/floors", json={"number": 1, "name": "Ground Floor"})
    assert create.status_code == 201
    data = create.get_json()
    assert data["number"] == 1
    assert data["name"] == "Ground Floor"
    assert data["active"] is True
    floor_id = data["id"]

    list_resp = client.get("/api/admin/floors")
    assert list_resp.status_code == 200
    floors = list_resp.get_json()
    assert any(f["id"] == floor_id for f in floors)


def test_admin_can_update_floor(app, client):
    _create_admin(app)
    _login(client)

    create = client.post("/api/admin/floors", json={"number": 2, "name": "Second Floor"})
    floor_id = create.get_json()["id"]

    update = client.patch(f"/api/admin/floors/{floor_id}", json={"number": 2, "name": "Upper Floor", "active": False})
    assert update.status_code == 200
    assert update.get_json()["name"] == "Upper Floor"
    assert update.get_json()["active"] is False


def test_admin_can_delete_empty_floor(app, client):
    _create_admin(app)
    _login(client)

    create = client.post("/api/admin/floors", json={"number": 3, "name": "Empty Floor"})
    floor_id = create.get_json()["id"]

    delete = client.delete(f"/api/admin/floors/{floor_id}")
    assert delete.status_code == 204

    floors = client.get("/api/admin/floors").get_json()
    assert not any(f["id"] == floor_id for f in floors)


def test_admin_force_delete_floor_cascades_zones_and_tables(app, client):
    _create_admin(app)
    _login(client)

    floor = client.post("/api/admin/floors", json={"number": 4, "name": "Cascade Floor"}).get_json()
    floor_id = floor["id"]
    floor_number = floor["number"]

    zone = client.post("/api/admin/zones", json={"floor": floor_number, "name": "Zone A"}).get_json()
    zone_id = zone["id"]

    table = client.post(
        "/api/admin/tables",
        json={"number": 10, "capacity": 4, "floor": floor_number, "zone": "Zone A"},
    ).get_json()
    table_id = table["id"]

    delete = client.delete(f"/api/admin/floors/{floor_id}?force=1")
    assert delete.status_code == 204

    tables = client.get(f"/api/admin/tables?floor={floor_id}").get_json()
    assert not any(t["id"] == table_id for t in tables)

    zones = client.get(f"/api/admin/zones?floor={floor_id}").get_json()
    assert not any(z["id"] == zone_id for z in zones)


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------

def test_admin_can_create_and_list_zones(app, client):
    _create_admin(app)
    _login(client)

    floor = client.post("/api/admin/floors", json={"number": 5, "name": "Floor Five"}).get_json()
    floor_number = floor["number"]

    create = client.post("/api/admin/zones", json={"floor": floor_number, "name": "Zone B"})
    assert create.status_code == 201
    zone = create.get_json()
    assert zone["name"] == "Zone B"
    assert zone["floor"] == floor_number
    zone_id = zone["id"]

    list_resp = client.get("/api/admin/zones")
    assert list_resp.status_code == 200
    assert any(z["id"] == zone_id for z in list_resp.get_json())


def test_admin_can_filter_zones_by_floor(app, client):
    _create_admin(app)
    _login(client)

    floor_a = client.post("/api/admin/floors", json={"number": 6, "name": "Floor A"}).get_json()
    floor_b = client.post("/api/admin/floors", json={"number": 7, "name": "Floor B"}).get_json()

    client.post("/api/admin/zones", json={"floor": floor_a["number"], "name": "Zone-A1"})
    client.post("/api/admin/zones", json={"floor": floor_b["number"], "name": "Zone-B1"})

    resp = client.get(f"/api/admin/zones?floor={floor_a['id']}")
    assert resp.status_code == 200
    zones = resp.get_json()
    assert all(z["floor"] == floor_a["number"] for z in zones)


def test_admin_can_update_zone(app, client):
    _create_admin(app)
    _login(client)

    floor = client.post("/api/admin/floors", json={"number": 8, "name": "Floor Eight"}).get_json()
    zone = client.post("/api/admin/zones", json={"floor": floor["number"], "name": "Old Zone"}).get_json()

    update = client.patch(f"/api/admin/zones/{zone['id']}", json={"floor": floor["number"], "name": "New Zone", "active": False})
    assert update.status_code == 200
    assert update.get_json()["name"] == "New Zone"
    assert update.get_json()["active"] is False


def test_admin_force_delete_zone_cascades_tables(app, client):
    _create_admin(app)
    _login(client)

    floor = client.post("/api/admin/floors", json={"number": 9, "name": "Floor Nine"}).get_json()
    zone = client.post("/api/admin/zones", json={"floor": floor["number"], "name": "Zone C"}).get_json()
    table = client.post(
        "/api/admin/tables",
        json={"number": 20, "capacity": 2, "floor": floor["number"], "zone": "Zone C"},
    ).get_json()
    table_id = table["id"]

    delete = client.delete(f"/api/admin/zones/{zone['id']}?force=1")
    assert delete.status_code == 204

    tables = client.get(f"/api/admin/tables?floor={floor['id']}").get_json()
    assert not any(t["id"] == table_id for t in tables)


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def test_admin_can_create_and_list_tables(app, client):
    _create_admin(app)
    _login(client)

    floor = client.post("/api/admin/floors", json={"number": 10, "name": "Floor Ten"}).get_json()
    client.post("/api/admin/zones", json={"floor": floor["number"], "name": "Main"})

    create = client.post(
        "/api/admin/tables",
        json={"number": 30, "capacity": 6, "floor": floor["number"], "zone": "Main"},
    )
    assert create.status_code == 201
    table = create.get_json()
    assert table["capacity"] == 6
    assert table["zone"] == "Main"
    table_id = table["id"]

    list_resp = client.get("/api/admin/tables")
    assert list_resp.status_code == 200
    assert any(t["id"] == table_id for t in list_resp.get_json())


def test_admin_can_filter_tables_by_floor(app, client):
    _create_admin(app)
    _login(client)

    floor_x = client.post("/api/admin/floors", json={"number": 11, "name": "Floor X"}).get_json()
    floor_y = client.post("/api/admin/floors", json={"number": 12, "name": "Floor Y"}).get_json()
    client.post("/api/admin/zones", json={"floor": floor_x["number"], "name": "Zx"})
    client.post("/api/admin/zones", json={"floor": floor_y["number"], "name": "Zy"})

    client.post("/api/admin/tables", json={"number": 40, "capacity": 4, "floor": floor_x["number"], "zone": "Zx"})
    client.post("/api/admin/tables", json={"number": 41, "capacity": 4, "floor": floor_y["number"], "zone": "Zy"})

    resp = client.get(f"/api/admin/tables?floor={floor_x['id']}")
    assert resp.status_code == 200
    tables = resp.get_json()
    assert all(t["floor"] == floor_x["number"] for t in tables)


def test_admin_can_update_table(app, client):
    _create_admin(app)
    _login(client)

    floor = client.post("/api/admin/floors", json={"number": 13, "name": "Floor Thirteen"}).get_json()
    client.post("/api/admin/zones", json={"floor": floor["number"], "name": "Zold"})
    client.post("/api/admin/zones", json={"floor": floor["number"], "name": "Znew"})
    table = client.post(
        "/api/admin/tables",
        json={"number": 50, "capacity": 2, "floor": floor["number"], "zone": "Zold"},
    ).get_json()

    update = client.patch(
        f"/api/admin/tables/{table['id']}",
        json={"number": 50, "capacity": 8, "floor": floor["number"], "zone": "Znew"},
    )
    assert update.status_code == 200
    assert update.get_json()["capacity"] == 8
    assert update.get_json()["zone"] == "Znew"


def test_admin_can_force_delete_table(app, client):
    _create_admin(app)
    _login(client)

    floor = client.post("/api/admin/floors", json={"number": 14, "name": "Floor Fourteen"}).get_json()
    client.post("/api/admin/zones", json={"floor": floor["number"], "name": "Zdel"})
    table = client.post(
        "/api/admin/tables",
        json={"number": 60, "capacity": 4, "floor": floor["number"], "zone": "Zdel"},
    ).get_json()
    table_id = table["id"]

    delete = client.delete(f"/api/admin/tables/{table_id}?force=1")
    assert delete.status_code == 204

    tables = client.get("/api/admin/tables").get_json()
    assert not any(t["id"] == table_id for t in tables)


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

def test_unauthenticated_cannot_access_floor_zone_table_management(app, client):
    for method, path in [
        ("GET", "/api/admin/floors"),
        ("POST", "/api/admin/floors"),
        ("GET", "/api/admin/zones"),
        ("POST", "/api/admin/zones"),
        ("GET", "/api/admin/tables"),
        ("POST", "/api/admin/tables"),
    ]:
        resp = getattr(client, method.lower())(path, json={})
        assert resp.status_code in (401, 403), f"Expected 401/403 for {method} {path}, got {resp.status_code}"


def test_customer_cannot_access_floor_zone_table_management(app, client):
    with app.app_context():
        user = UserDB(
            role="customer",
            name="Customer",
            email="customer@floor-tests.example.com",
            password_hash=hash_password("CustomerPass123"),
        )
        db.session.add(user)
        db.session.commit()

    client.post("/api/auth/login", json={"email": "customer@floor-tests.example.com", "password": "CustomerPass123"})

    for method, path in [
        ("GET", "/api/admin/floors"),
        ("POST", "/api/admin/floors"),
        ("GET", "/api/admin/zones"),
        ("POST", "/api/admin/zones"),
        ("GET", "/api/admin/tables"),
        ("POST", "/api/admin/tables"),
    ]:
        resp = getattr(client, method.lower())(path, json={})
        assert resp.status_code in (401, 403), f"Expected 401/403 for {method} {path}, got {resp.status_code}"
