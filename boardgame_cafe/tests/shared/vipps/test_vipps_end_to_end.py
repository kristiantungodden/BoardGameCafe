import json
from unittest.mock import patch

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.payments.infrastructure.vipps import VippsAdapter
from features.payments.presentation.api.payment_routes import configure_payment_provider


def _make_fake_post(order_id="order-abc", capture_ok=True):
    def fake_post(url, headers=None, json=None, timeout=None):
        class R:
            def __init__(self, data=None, status=200):
                self._data = data or {}
                self.status_code = status

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception("http error")

            def json(self):
                return self._data

        if url.endswith("/accesstoken/get"):
            return R({"access_token": "tok-1"})
        if url.endswith("/ecomm/v2/payments"):
            return R({"orderId": order_id, "url": "https://pay"})
        if url.endswith("/capture"):
            return R({}, 200 if capture_ok else 400)
        if url.endswith("/refund"):
            return R({}, 200)
        return R({}, 404)

    return fake_post


def _make_fake_put(cancel_ok=True):
    def fake_put(url, headers=None, json=None, timeout=None):
        class R:
            def __init__(self, status=200):
                self.status_code = status

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception("http error")

            def json(self):
                return {}

        if url.endswith("/cancel"):
            return R(200 if cancel_ok else 400)
        return R(404)

    return fake_put


def test_end_to_end_capture_flow(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        payment = Payment(table_reservation_id=42, amount_cents=2500)
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

    # Mock token, initiate and capture
    monkeypatch.setattr("requests.post", _make_fake_post(order_id="order-xyz", capture_ok=True))
    monkeypatch.setattr("requests.put", _make_fake_put(cancel_ok=True))  # unused here but safe

    # Start payment
    resp = client.post(f"/api/payments/start/{saved.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["provider"] == "vipps"
    provider_ref = data["provider_ref"]
    assert provider_ref == "order-xyz"

    # Capture payment (simulate idempotency header)
    headers = {"X-Request-Id": "req-capture-1"}
    cap_resp = client.post(f"/api/payments/capture/{saved.id}", headers=headers)
    assert cap_resp.status_code == 200

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.PAID


def test_end_to_end_cancel_flow(client, app, monkeypatch):
    repo = PaymentRepository()
    with app.app_context():
        payment = Payment(table_reservation_id=99, amount_cents=1800)
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

    # Mock token, initiate and cancel
    monkeypatch.setattr("requests.post", _make_fake_post(order_id="order-cancel", capture_ok=True))
    monkeypatch.setattr("requests.put", _make_fake_put(cancel_ok=True))

    # Start payment
    resp = client.post(f"/api/payments/start/{saved.id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["provider"] == "vipps"
    provider_ref = data["provider_ref"]
    assert provider_ref == "order-cancel"

    # Cancel payment
    headers = {"X-Request-Id": "req-cancel-1"}
    cancel_resp = client.post(f"/api/payments/cancel/{saved.id}", headers=headers)
    assert cancel_resp.status_code == 200

    with app.app_context():
        updated = repo.get_by_id(saved.id)
        assert updated.status == PaymentStatus.FAILED
