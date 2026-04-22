from datetime import datetime, timedelta
from types import SimpleNamespace

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db


def _create_customer_and_login(client, app, email: str = "customer@example.com") -> UserDB:
    with app.app_context():
        user = UserDB(name="Customer", email=email, password_hash="hashed", role="customer")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True

    with app.app_context():
        return db.session.get(UserDB, user_id)


def _create_booking_for_customer(customer_id: int) -> BookingDB:
    start_ts = datetime(2026, 4, 22, 12, 0, 0)
    end_ts = start_ts + timedelta(hours=2)
    booking = BookingDB(
        customer_id=customer_id,
        start_ts=start_ts,
        end_ts=end_ts,
        party_size=2,
        status="confirmed",
    )
    db.session.add(booking)
    db.session.commit()
    return booking


def test_payment_success_route_is_read_only_and_uses_db_status(client, app, monkeypatch):
    repo = PaymentRepository()
    customer = _create_customer_and_login(client, app)

    with app.app_context():
        booking = _create_booking_for_customer(customer.id)
        payment = Payment(booking_id=booking.id, amount_cents=2300)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_success"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

    monkeypatch.setattr(
        "app.stripe.checkout.Session.retrieve",
        lambda session_id: SimpleNamespace(payment_status="paid"),
    )

    resp = client.get(f"/payments/success/{saved.id}")

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Payment Confirmation" in html
    assert "Payment is being verified" in html
    assert "pending" in html

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PENDING


def test_payment_success_route_handles_unpaid_status(client, app, monkeypatch):
    repo = PaymentRepository()
    customer = _create_customer_and_login(client, app, email="pending@example.com")

    with app.app_context():
        booking = _create_booking_for_customer(customer.id)
        payment = Payment(booking_id=booking.id, amount_cents=2400)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_pending"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

    monkeypatch.setattr(
        "app.stripe.checkout.Session.retrieve",
        lambda session_id: SimpleNamespace(payment_status="unpaid"),
    )

    resp = client.get(f"/payments/success/{saved.id}")

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Payment is being verified" in html
    assert "pending" in html

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PENDING


def test_payment_cancel_route_renders_cancelled_page_without_login(client):
    resp = client.get("/payments/cancel/11")
    assert resp.status_code in {301, 302}


def test_payment_result_routes_require_payment_owner(client, app):
    repo = PaymentRepository()

    customer = _create_customer_and_login(client, app, email="owner@example.com")
    with app.app_context():
        booking = _create_booking_for_customer(customer.id)
        payment = Payment(booking_id=booking.id, amount_cents=1500)
        saved = repo.add(payment)

        stranger = UserDB(
            name="Stranger",
            email="stranger@example.com",
            password_hash="hashed",
            role="customer",
        )
        db.session.add(stranger)
        db.session.commit()
        stranger_id = stranger.id

    with client.session_transaction() as session:
        session["_user_id"] = str(stranger_id)
        session["_fresh"] = True

    resp = client.get(f"/payments/success/{saved.id}")
    assert resp.status_code == 403


def test_payment_success_query_url_redirects_to_canonical_path(client, app):
    repo = PaymentRepository()
    customer = _create_customer_and_login(client, app, email="canonical@example.com")

    with app.app_context():
        booking = _create_booking_for_customer(customer.id)
        payment = Payment(booking_id=booking.id, amount_cents=1900)
        saved = repo.add(payment)

    resp = client.get(
        f"/payments/success?payment_id={saved.id}&booking_id={saved.booking_id}&session_id=cs_test",
        follow_redirects=False,
    )

    assert resp.status_code in {301, 302}
    assert resp.headers["Location"].endswith(f"/payments/success/{saved.id}")
