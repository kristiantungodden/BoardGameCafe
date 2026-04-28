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


def test_stripe_webhook_marks_payment_paid(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        _create_created_booking(booking_id=321)
        payment = Payment(booking_id=321, amount_cents=1500)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_webhook"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

    def fake_construct_event(payload, sig_header, secret):
        assert sig_header == "t=123,v1=fake"
        return {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"payment_id": str(saved.id)}}},
        }

    monkeypatch.setattr(
        "features.payments.presentation.stripe.stripe_webhook.stripe.Webhook.construct_event",
        fake_construct_event,
    )

    resp = client.post(
        "/payments/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "t=123,v1=fake", "Content-Type": "application/json"},
    )

    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated is not None
        assert updated.status == PaymentStatus.PAID
        booking = db.session.get(BookingDB, 321)
        assert booking is not None
        assert booking.status == "confirmed"


def test_stripe_webhook_expired_session_deletes_created_booking(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        _create_created_booking(booking_id=654)
        payment = Payment(booking_id=654, amount_cents=1500)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_expired"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

    def fake_construct_event(payload, sig_header, secret):
        return {
            "type": "checkout.session.expired",
            "data": {"object": {"metadata": {"payment_id": str(saved.id)}}},
        }

    monkeypatch.setattr(
        "features.payments.presentation.stripe.stripe_webhook.stripe.Webhook.construct_event",
        fake_construct_event,
    )

    resp = client.post(
        "/payments/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "t=123,v1=fake", "Content-Type": "application/json"},
    )

    assert resp.status_code == 200

    with app.app_context():
        assert repo.get_by_id(saved.id) is None
        assert db.session.get(BookingDB, 654) is None


def test_stripe_webhook_rejects_invalid_signature(client, monkeypatch):
    def fake_construct_event(payload, sig_header, secret):
        raise ValueError("invalid signature")

    monkeypatch.setattr(
        "features.payments.presentation.stripe.stripe_webhook.stripe.Webhook.construct_event",
        fake_construct_event,
    )

    resp = client.post(
        "/payments/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "invalid", "Content-Type": "application/json"},
    )

    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Invalid webhook"}
