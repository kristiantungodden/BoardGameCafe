from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository


def test_stripe_webhook_marks_payment_paid(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
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
        "features.payments.infrastructure.stripe.stripe_webhook.stripe.Webhook.construct_event",
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


def test_stripe_webhook_rejects_invalid_signature(client, monkeypatch):
    def fake_construct_event(payload, sig_header, secret):
        raise ValueError("invalid signature")

    monkeypatch.setattr(
        "features.payments.infrastructure.stripe.stripe_webhook.stripe.Webhook.construct_event",
        fake_construct_event,
    )

    resp = client.post(
        "/payments/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "invalid", "Content-Type": "application/json"},
    )

    assert resp.status_code == 400
    assert resp.get_json() == {"error": "Invalid webhook"}
