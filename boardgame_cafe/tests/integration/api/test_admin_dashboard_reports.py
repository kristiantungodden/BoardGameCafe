from datetime import datetime, timezone, timedelta

from features.users.infrastructure import UserDB, hash_password
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.payments.infrastructure.database.payments_db import PaymentDB
from shared.infrastructure import db


def _create_admin(app, *, email="admin@report-tests.example.com", password="AdminPass123"):
    with app.app_context():
        user = UserDB(
            role="admin",
            name="Admin",
            email=email,
            password_hash=hash_password(password),
        )
        db.session.add(user)
        db.session.commit()
        return int(user.id)


def _login(client, *, email="admin@report-tests.example.com", password="AdminPass123"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


def _create_booking_with_payment(app, *, customer_id: int, amount_cents: int = 10000):
    """Helper: inserts a confirmed booking and a paid payment, returns booking id."""
    with app.app_context():
        now = datetime.now(timezone.utc)
        booking = BookingDB(
            customer_id=customer_id,
            start_ts=now + timedelta(hours=1),
            end_ts=now + timedelta(hours=3),
            party_size=2,
            status="confirmed",
        )
        db.session.add(booking)
        db.session.flush()
        payment = PaymentDB(
            booking_id=int(booking.id),
            type="online",
            provider="stripe",
            amount_cents=amount_cents,
            currency="NOK",
            status="paid",
            provider_ref="test-ref-001",
        )
        db.session.add(payment)
        db.session.commit()
        return int(booking.id)


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

def test_admin_can_get_dashboard_stats(app, client):
    _create_admin(app)
    _login(client)

    resp = client.get("/api/admin/dashboard/stats")
    assert resp.status_code == 200
    data = resp.get_json()

    # All expected top-level keys present
    for key in (
        "users_total",
        "users_by_role",
        "games_total",
        "copies_total",
        "copies_by_status",
        "tables_total",
        "tables_by_status",
        "bookings_total",
        "bookings_by_status",
        "open_incidents",
        "published_announcements",
        "generated_at",
    ):
        assert key in data, f"Missing key: {key}"

    # At least the seeded admin is counted
    assert data["users_total"] >= 1
    assert data["users_by_role"]["admin"] >= 1


def test_dashboard_stats_counts_reflect_seeded_data(app, client):
    admin_id = _create_admin(app)
    _login(client)

    # Create an extra customer user
    with app.app_context():
        customer = UserDB(
            role="customer",
            name="Customer",
            email="customer@report-tests.example.com",
            password_hash=hash_password("CustPass123"),
        )
        db.session.add(customer)
        db.session.commit()
        customer_id = int(customer.id)

    _create_booking_with_payment(app, customer_id=customer_id)

    resp = client.get("/api/admin/dashboard/stats")
    data = resp.get_json()
    assert data["users_by_role"]["customer"] >= 1
    assert data["bookings_total"] >= 1


def test_non_admin_cannot_access_dashboard_stats(app, client):
    with app.app_context():
        user = UserDB(
            role="customer",
            name="Customer",
            email="customer@stats-tests.example.com",
            password_hash=hash_password("CustomerPass123"),
        )
        db.session.add(user)
        db.session.commit()

    client.post("/api/auth/login", json={"email": "customer@stats-tests.example.com", "password": "CustomerPass123"})
    resp = client.get("/api/admin/dashboard/stats")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Registration report
# ---------------------------------------------------------------------------

def test_admin_can_get_registration_report(app, client):
    admin_id = _create_admin(app)
    _login(client)

    # Create an extra user so there's at least one registration to count
    with app.app_context():
        u = UserDB(
            role="customer",
            name="Reg User",
            email="reg@report-tests.example.com",
            password_hash=hash_password("RegPass123"),
        )
        db.session.add(u)
        db.session.commit()

    resp = client.get("/api/admin/reports/registrations?days=7")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 7

    today = str(datetime.now(timezone.utc).date())
    today_entry = next((d for d in data if d["date"] == today), None)
    assert today_entry is not None
    assert today_entry["new_users"] >= 1
    assert today_entry["cumulative"] >= 1


def test_non_admin_cannot_access_registration_report(app, client):
    with app.app_context():
        user = UserDB(
            role="customer",
            name="Customer",
            email="customer@reg-report-tests.example.com",
            password_hash=hash_password("CustomerPass123"),
        )
        db.session.add(user)
        db.session.commit()

    client.post("/api/auth/login", json={"email": "customer@reg-report-tests.example.com", "password": "CustomerPass123"})
    resp = client.get("/api/admin/reports/registrations")
    assert resp.status_code in (401, 403)


def test_reports_registrations_malformed_days_defaults_to_30(app, client):
    _create_admin(app)
    _login(client)

    resp = client.get("/api/admin/reports/registrations?days=invalid")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 30


# ---------------------------------------------------------------------------
# Revenue report
# ---------------------------------------------------------------------------

def test_admin_can_get_revenue_report(app, client):
    admin_id = _create_admin(app)
    _login(client)

    with app.app_context():
        customer = UserDB(
            role="customer",
            name="Payer",
            email="payer@report-tests.example.com",
            password_hash=hash_password("PayerPass123"),
        )
        db.session.add(customer)
        db.session.commit()
        customer_id = int(customer.id)

    _create_booking_with_payment(app, customer_id=customer_id, amount_cents=5000)

    resp = client.get("/api/admin/reports/revenue?days=7")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 7

    today = str(datetime.now(timezone.utc).date())
    today_entry = next((d for d in data if d["date"] == today), None)
    assert today_entry is not None
    assert today_entry["total_cents"] >= 5000


def test_non_admin_cannot_access_revenue_report(app, client):
    with app.app_context():
        user = UserDB(
            role="customer",
            name="Customer",
            email="customer@rev-report-tests.example.com",
            password_hash=hash_password("CustomerPass123"),
        )
        db.session.add(user)
        db.session.commit()

    client.post("/api/auth/login", json={"email": "customer@rev-report-tests.example.com", "password": "CustomerPass123"})
    resp = client.get("/api/admin/reports/revenue")
    assert resp.status_code in (401, 403)


def test_reports_revenue_empty_dataset_returns_zero_series(app, client):
    _create_admin(app)
    _login(client)

    resp = client.get("/api/admin/reports/revenue?days=5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 5
    assert all(item["total_cents"] == 0 for item in data)


# ---------------------------------------------------------------------------
# Top games report
# ---------------------------------------------------------------------------

def test_admin_can_get_top_games_report(app, client):
    _create_admin(app)
    _login(client)

    resp = client.get("/api/admin/reports/top-games?days=30")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "by_rating" in data
    assert "by_bookings" in data
    assert isinstance(data["by_rating"], list)
    assert isinstance(data["by_bookings"], list)


def test_non_admin_cannot_access_top_games_report(app, client):
    with app.app_context():
        user = UserDB(
            role="customer",
            name="Customer",
            email="customer@topgames-tests.example.com",
            password_hash=hash_password("CustomerPass123"),
        )
        db.session.add(user)
        db.session.commit()

    client.post("/api/auth/login", json={"email": "customer@topgames-tests.example.com", "password": "CustomerPass123"})
    resp = client.get("/api/admin/reports/top-games")
    assert resp.status_code in (401, 403)


def test_reports_top_games_empty_dataset_returns_empty_lists(app, client):
    _create_admin(app)
    _login(client)

    resp = client.get("/api/admin/reports/top-games?days=0")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["by_rating"] == []
    assert data["by_bookings"] == []


# ---------------------------------------------------------------------------
# Revenue CSV export
# ---------------------------------------------------------------------------

def test_admin_can_export_revenue_csv(app, client):
    admin_id = _create_admin(app)
    _login(client)

    with app.app_context():
        customer = UserDB(
            role="customer",
            name="CSV Payer",
            email="csvpayer@report-tests.example.com",
            password_hash=hash_password("CsvPass123"),
        )
        db.session.add(customer)
        db.session.commit()
        customer_id = int(customer.id)

    _create_booking_with_payment(app, customer_id=customer_id, amount_cents=9900)

    resp = client.get("/api/admin/reports/revenue/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
    body = resp.data.decode("utf-8")
    assert len(body) > 0
    assert "Revenue Report" in body


def test_non_admin_cannot_export_revenue_csv(app, client):
    with app.app_context():
        user = UserDB(
            role="customer",
            name="Customer",
            email="customer@csv-tests.example.com",
            password_hash=hash_password("CustomerPass123"),
        )
        db.session.add(user)
        db.session.commit()

    client.post("/api/auth/login", json={"email": "customer@csv-tests.example.com", "password": "CustomerPass123"})
    resp = client.get("/api/admin/reports/revenue/csv")
    assert resp.status_code in (401, 403)
