import json

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository


def test_vipps_callback_updates_payment_status(client, app):
    repo = PaymentRepository()
    with app.app_context():
        # Create and save a payment
        payment = Payment(booking_id=42, amount_cents=1500)
        saved = repo.add(payment)
        # Set provider_ref to simulate earlier initiation
        saved.provider = "vipps"
        saved.provider_ref = "order-xyz"
        repo.update(saved)

    # Post callback from Vipps
    payload = {
        "merchantSerialNumber": "123456",
        "orderId": "order-xyz",
        "transactionInfo": {"amount": 1500, "status": "RESERVED", "transactionId": "tx-1"},
    }

    resp = client.post("/api/payments/vipps/callback/v2/payments/order-xyz", json=payload)
    assert resp.status_code == 200

    with app.app_context():
        updated = repo.get_by_provider_ref("order-xyz")
        assert updated is not None
        assert updated.status == PaymentStatus.PAID
