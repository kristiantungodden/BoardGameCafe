import json
from unittest.mock import patch

import pytest

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.vipps import VippsAdapter


def test_start_payment_and_fetch_status(monkeypatch):
    adapter = VippsAdapter(
        base_url="https://api.vipps.no",
        subscription_key="subkey",
        client_id="cid",
        client_secret="csecret",
        merchant_serial_number="123456",
        callback_prefix="https://example.com/vipps/callback",
    )

    # Mock token response and initiate response
    def mock_post(url, headers=None, json=None, timeout=None):
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
            return R({"access_token": "tok-123"})
        if url.endswith("/ecomm/v2/payments"):
            return R({"orderId": "order-abc", "url": "https://api.vipps.no/dwo..."})
        return R({}, 404)

    with patch("requests.post", side_effect=mock_post):
        payment = Payment(table_reservation_id=1, amount_cents=5000, id=10)
        order_id = adapter.start_payment(payment)
        assert order_id == "order-abc"

    # Mock details GET to show reserved/captured
    def mock_get(url, headers=None, timeout=None):
        class R:
            def __init__(self, data):
                self._data = data
                self.status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return self._data

        return R({
            "orderId": "order-abc",
            "transactionLogHistory": [
                {"transactionInfo": {"status": "RESERVE", "amount": 5000}}
            ],
        })

    with patch("requests.get", side_effect=mock_get):
        status = adapter.fetch_status("order-abc")
        assert status == PaymentStatus.PAID
