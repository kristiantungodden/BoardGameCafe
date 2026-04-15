from types import SimpleNamespace

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository


def test_payment_success_route_verifies_stripe_and_updates_paid(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
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


def test_payment_success_route_handles_unpaid_status(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
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
    assert "Payment is being verified" in html
    assert "pending" in html

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PENDING


def test_payment_cancel_route_renders_cancelled_page_without_login(client):
    resp = client.get("/payments/cancel?payment_id=11&booking_id=7")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Payment Cancelled" in html
    assert "Payment was cancelled" in html
