import requests
from features.payments.infrastructure.vipps.vipps_client import VippsClient
from features.payments.infrastructure.vipps.vipps_config import VippsConfig


def test_initiate_and_get_details(monkeypatch):
    cfg = VippsConfig(base_url="https://api.vipps.no", subscription_key="sub", client_id="cid", client_secret="csec", merchant_serial_number="m123", callback_prefix="https://cb")
    client = VippsClient(cfg)

    def fake_post(url, json=None, headers=None, timeout=None):
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
            return R({"orderId": "order-xyz", "url": "https://pay"})
        return R({}, 404)

    def fake_get(url, headers=None, timeout=None):
        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"orderId": "order-xyz", "transactionLogHistory": [{"transactionInfo": {"status": "RESERVE", "amount": 1000}}]}

        return R()

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests, "get", fake_get)

    data = client.initiate_payment({"transaction": {"amount": 1000}})
    assert data["orderId"] == "order-xyz"

    details = client.get_details("order-xyz")
    assert details["orderId"] == "order-xyz"
    assert details["transactionLogHistory"][0]["transactionInfo"]["status"] == "RESERVE"
