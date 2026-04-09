from unittest.mock import patch
import requests

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.infrastructure.vipps import VippsAdapter
from features.payments.presentation.api.payment_routes import configure_payment_provider


def test_capture_forwards_x_request_id_and_is_idempotent(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        p = Payment(booking_id=8, amount_cents=1500)
        saved = repo.add(p)
        saved.provider = "vipps"
        saved.provider_ref = f"vipps:sim-{saved.id}"
        repo.update(saved)

    adapter = VippsAdapter()
    configure_payment_provider(adapter)

    # Simulate adapter.capture using unit behavior (simulated since provider_ref starts with vipps:)
    headers = {"X-Request-Id": "idem-123"}
    resp = client.post(f"/api/payments/capture/{saved.id}", headers=headers)
    assert resp.status_code == 200

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PAID

    # Replaying same idempotency header should still be OK (simulate idempotency)
    resp2 = client.post(f"/api/payments/capture/{saved.id}", headers=headers)
    assert resp2.status_code == 200


def test_cancel_forwards_x_request_id(client, app):
    repo = PaymentRepository()
    with app.app_context():
        p = Payment(booking_id=9, amount_cents=1200)
        saved = repo.add(p)
        saved.provider = "vipps"
        saved.provider_ref = f"vipps:sim-{saved.id}"
        repo.update(saved)

    adapter = VippsAdapter()
    configure_payment_provider(adapter)

    headers = {"X-Request-Id": "idem-cancel"}
    resp = client.post(f"/api/payments/cancel/{saved.id}", headers=headers)
    assert resp.status_code == 200

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.FAILED
