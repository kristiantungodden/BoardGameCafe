from types import SimpleNamespace
from datetime import datetime

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from shared.infrastructure import db


def _create_created_booking(booking_id: int) -> BookingDB:
    booking = BookingDB(
        id=booking_id,
        customer_id=1,
        start_ts=datetime(2026, 4, 20, 18, 0),
        end_ts=datetime(2026, 4, 20, 20, 0),
        party_size=2,
        status="created",
    )
    db.session.add(booking)
    db.session.commit()
    return booking


def test_payment_success_route_verifies_stripe_and_updates_paid(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        _create_created_booking(booking_id=45)
        payment = Payment(booking_id=45, amount_cents=2300)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_success"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

    monkeypatch.setattr(
        "app.stripe.checkout.Session.retrieve",
        lambda session_id: SimpleNamespace(payment_status="paid"),
    )

    resp = client.get(
        f"/payments/success?payment_id={saved.id}&booking_id={saved.booking_id}&session_id=cs_test_success"
    )

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Payment Confirmation" in html
    assert "Payment completed successfully." in html
    assert "success" in html

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PAID
        booking = db.session.get(BookingDB, 45)
        assert booking is not None
        assert booking.status == "confirmed"


def test_payment_success_route_handles_unpaid_status_by_cleaning_created_booking(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        _create_created_booking(booking_id=46)
        payment = Payment(booking_id=46, amount_cents=2400)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_pending"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

    monkeypatch.setattr(
        "app.stripe.checkout.Session.retrieve",
        lambda session_id: SimpleNamespace(payment_status="unpaid"),
    )

    resp = client.get(
        f"/payments/success?payment_id={saved.id}&booking_id={saved.booking_id}&session_id=cs_test_pending"
    )

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Payment failed" in html
    assert "failed" in html

    with app.app_context():
        assert repo.get_by_id(saved.id) is None
        assert db.session.get(BookingDB, 46) is None


def test_payment_cancel_route_deletes_created_booking_without_login(client, app):
    repo = PaymentRepository()
    with app.app_context():
        _create_created_booking(booking_id=7)
        payment = Payment(booking_id=7, amount_cents=1500)
        saved = repo.add(payment)
        saved.status = PaymentStatus.PENDING
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_cancel"
        repo.update(saved)

    resp = client.get(f"/payments/cancel?payment_id={saved.id}&booking_id=7")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Payment Cancelled" in html
    assert "Payment was cancelled" in html

    with app.app_context():
        assert repo.get_by_id(saved.id) is None
        assert db.session.get(BookingDB, 7) is None
