from unittest.mock import patch

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository


def test_capture_and_cancel_routes(client, app):
    repo = PaymentRepository()
    with app.app_context():
        payment = Payment(booking_id=5, amount_cents=2000)
        saved = repo.add(payment)
        # set a simulated provider_ref to trigger simulated flows
        saved.provider = "vipps"
        saved.provider_ref = f"vipps:sim-{saved.id}"
        repo.update(saved)

    # Capture: since provider_ref starts with vipps: adapter will simulate and return True
    headers = {"X-Request-Id": "req-1"}
    resp = client.post(f"/api/payments/capture/{saved.id}", headers=headers)
    assert resp.status_code == 200

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PAID

    # Prepare another payment to cancel
    with app.app_context():
        p2 = Payment(booking_id=6, amount_cents=1000)
        s2 = repo.add(p2)
        s2.provider = "vipps"
        s2.provider_ref = f"vipps:sim-{s2.id}"
        repo.update(s2)

    headers2 = {"X-Request-Id": "req-2"}
    resp2 = client.post(f"/api/payments/cancel/{s2.id}", headers=headers2)
    assert resp2.status_code == 200

    with app.app_context():
        updated2 = repo.get_by_id(s2.id)
        assert updated2.status == PaymentStatus.FAILED
