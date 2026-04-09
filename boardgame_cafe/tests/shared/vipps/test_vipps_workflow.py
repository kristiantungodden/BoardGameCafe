import json
from unittest.mock import patch

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.infrastructure.vipps import VippsAdapter
from features.payments.presentation.api.payment_routes import configure_payment_provider


def test_start_route_and_webhook_updates_status(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        payment = Payment(booking_id=7, amount_cents=3000)
        saved = repo.add(payment)

    adapter = VippsAdapter(
        base_url="https://api.vipps.no",
        subscription_key="subkey",
        client_id="cid",
        client_secret="csecret",
        merchant_serial_number="m123",
        callback_prefix="https://example.com/vipps/callback",
    )
    configure_payment_provider(adapter)

    # Mock token and initiate
    def fake_post(url, headers=None, json=None, timeout=None):
        class R:
            def __init__(self, data, status=200):
                self._data = data
                self.status_code = status

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception("http error")

            def json(self):
                return self._data

        if url.endswith("/accesstoken/get"):
            return R({"access_token": "tok-1"})
        if url.endswith("/ecomm/v2/payments"):
            return R({"orderId": "order-abc", "url": "https://pay"})
        return R({}, 404)

    monkeypatch.setattr("requests.post", fake_post)

    # Call start route
    resp = client.post(f"/api/payments/start/{saved.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["provider"] == "vipps"
    assert data["provider_ref"] == "order-abc"
    assert data["status"].lower() == "pending"

    # Simulate Vipps callback with RESERVE => should update payment to PAID
    payload = {"transactionInfo": {"status": "RESERVE", "amount": 3000}}
    cb_resp = client.post(f"/api/payments/vipps/callback/v2/payments/order-abc", json=payload)
    assert cb_resp.status_code == 200

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PAID
