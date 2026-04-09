import os

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository


def test_vipps_callback_requires_auth(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        payment = Payment(booking_id=7, amount_cents=1200)
        saved = repo.add(payment)
        saved.provider = "vipps"
        saved.provider_ref = "order-auth"
        repo.update(saved)

    # Set expected token
    monkeypatch.setenv("VIPPS_CALLBACK_AUTH_TOKEN", "Bearer secret-token")

    payload = {
        "merchantSerialNumber": "123456",
        "orderId": "order-auth",
        "transactionInfo": {"amount": 1200, "status": "RESERVED", "transactionId": "tx-9"},
    }

    # Missing Authorization header => forbidden
    resp = client.post("/api/payments/vipps/callback/v2/payments/order-auth", json=payload)
    assert resp.status_code == 403

    # Provide correct Authorization header => accepted
    headers = {"Authorization": "Bearer secret-token"}
    resp2 = client.post("/api/payments/vipps/callback/v2/payments/order-auth", json=payload, headers=headers)
    assert resp2.status_code == 200

    with app.app_context():
        updated = repo.get_by_provider_ref("order-auth")
        assert updated.status == PaymentStatus.PAID
