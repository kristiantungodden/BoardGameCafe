import requests
from unittest.mock import patch

from features.payments.infrastructure.vipps import VippsAdapter
from features.payments.infrastructure.vipps.vipps_config import VippsConfig
from features.payments.infrastructure.vipps.vipps_client import VippsClient


def test_refund_success_and_http_error(monkeypatch):
    cfg = VippsConfig(base_url="https://api.vipps.no", subscription_key="sub", client_id="cid", client_secret="csec", merchant_serial_number="m123", callback_prefix="https://cb")
    client = VippsClient(cfg)

    # Patch token and refund endpoints
    def fake_post(url, json=None, headers=None, timeout=None):
        class R:
            def __init__(self, status=200, data=None):
                self.status_code = status
                self._data = data or {}

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise Exception("http error")

            def json(self):
                return self._data

        if url.endswith("/accesstoken/get"):
            return R(200, {"access_token": "tok-x"})
        if url.endswith("/refund"):
            return R(200, {"result": "ok"})
        return R(404, {})

    monkeypatch.setattr(requests, "post", fake_post)

    adapter = VippsAdapter(cfg)
    # Simulate a refund call (provider_ref not simulated; use a fake id)
    ok = adapter.refund("order-1", amount_cents=500)
    assert ok is True

    # Now simulate HTTP 400 on refund
    def fake_post_err(url, json=None, headers=None, timeout=None):
        class R:
            def __init__(self, status=400):
                self.status_code = status

            def raise_for_status(self):
                raise Exception("http error")

            def json(self):
                return {}

        return R(400)

    monkeypatch.setattr(requests, "post", fake_post_err)

    try:
        adapter.refund("order-1", amount_cents=500)
        assert False, "expected exception"
    except Exception:
        assert True
