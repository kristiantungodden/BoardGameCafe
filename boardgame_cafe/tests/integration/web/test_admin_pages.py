from features.users.infrastructure import UserDB, hash_password
from shared.infrastructure import db


def _create_user(app, *, role: str, email: str, password: str = "Pass123456"):
    with app.app_context():
        user = UserDB(
            role=role,
            name=role.capitalize(),
            email=email,
            password_hash=hash_password(password),
        )
        db.session.add(user)
        db.session.commit()


def _login(client, *, email: str, password: str = "Pass123456"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /admin — dashboard page
# ---------------------------------------------------------------------------

def test_admin_dashboard_redirects_unauthenticated(app, client):
    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code in (302, 301, 303)


def test_admin_dashboard_redirects_non_admin(app, client):
    _create_user(app, role="customer", email="cust@admin-page-tests.example.com")
    _login(client, email="cust@admin-page-tests.example.com")

    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code in (302, 301, 303)


def test_admin_dashboard_renders_for_admin(app, client):
    _create_user(app, role="admin", email="admin@admin-page-tests.example.com")
    _login(client, email="admin@admin-page-tests.example.com")

    resp = client.get("/admin", follow_redirects=False)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /admin/login — login page
# ---------------------------------------------------------------------------

def test_admin_login_page_renders_when_unauthenticated(app, client):
    resp = client.get("/admin/login")
    assert resp.status_code == 200


def test_admin_login_page_redirects_when_already_admin(app, client):
    _create_user(app, role="admin", email="admin@login-page-tests.example.com")
    _login(client, email="admin@login-page-tests.example.com")

    resp = client.get("/admin/login", follow_redirects=False)
    assert resp.status_code in (302, 301, 303)
    assert "/admin" in resp.headers.get("Location", "")
