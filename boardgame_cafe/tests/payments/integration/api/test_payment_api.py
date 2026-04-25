from __future__ import annotations

from datetime import datetime
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


def _create_booking_for_customer(customer_id: int, status: str = "confirmed") -> BookingDB:
    booking = BookingDB(
        customer_id=customer_id,
        start_ts=datetime(2026, 4, 22, 12, 0),
        end_ts=datetime(2026, 4, 22, 14, 0),
        party_size=2,
        status=status,
    )
    db.session.add(booking)
    db.session.commit()
    return booking


def test_payment_success_route_confirms_paid_booking_and_emits_publish_hook(client, app, monkeypatch):
    repo = PaymentRepository()
    customer = _create_customer_and_login(client, app)

    with app.app_context():
        booking = _create_booking_for_customer(customer.id, status="created")
        booking_id = booking.id
        payment = Payment(booking_id=booking.id, amount_cents=2300)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_success"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

    publish_mock = SimpleNamespace(calls=[])

    def fake_publish(booking_id):
        publish_mock.calls.append(booking_id)

    monkeypatch.setattr(
        "features.payments.composition.payment_use_case_factories.publish_reservation_payment_completed",
        fake_publish,
    )
    monkeypatch.setattr(
        "features.payments.infrastructure.stripe.stripe_adapter.stripe.checkout.Session.retrieve",
        lambda session_id: SimpleNamespace(payment_status="paid"),
    )

    resp = client.get(f"/payments/success/{saved.id}")

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Payment completed successfully." in html

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PAID
        booking_after_payment = db.session.get(BookingDB, booking_id)
        assert booking_after_payment is not None
        assert booking_after_payment.status == "confirmed"

    assert publish_mock.calls == [booking_id]


def test_payment_cancel_route_deletes_created_booking_aggregate(client, app):
    repo = PaymentRepository()
    customer = _create_customer_and_login(client, app, email="cancel-cleanup@example.com")

    with app.app_context():
        booking = _create_booking_for_customer(customer.id, status="created")
        payment = Payment(booking_id=booking.id, amount_cents=2400)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_cancel_cleanup"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

        booking_id = booking.id
        payment_id = saved.id

    resp = client.get(f"/payments/cancel/{payment_id}")

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Payment Cancelled" in html

    with app.app_context():
        assert repo.get_by_id(payment_id) is None
        assert db.session.get(BookingDB, booking_id) is None
