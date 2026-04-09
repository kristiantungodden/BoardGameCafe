import requests
from features.payments.infrastructure.vipps.vipps_auth import VippsAuth
from features.payments.infrastructure.vipps.vipps_config import VippsConfig


def test_get_access_token_and_headers(monkeypatch):
    cfg = VippsConfig(base_url="https://api.vipps.no", subscription_key="sub", client_id="cid", client_secret="csec", merchant_serial_number="m123", callback_prefix="https://cb")

    def fake_post(url, headers=None, timeout=None):
        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"access_token": "tok-123"}

        # assert token endpoint called
        assert url.endswith("/accesstoken/get")
        assert headers and headers.get("client_id") == "cid"
        return R()

    monkeypatch.setattr(requests, "post", fake_post)

    auth = VippsAuth(cfg)
    token = auth.get_access_token()
    assert token == "tok-123"
    headers = auth.auth_headers()
    assert headers["Authorization"] == "Bearer tok-123"
    assert headers["Ocp-Apim-Subscription-Key"] == "sub"
    assert headers["Merchant-Serial-Number"] == "m123"
