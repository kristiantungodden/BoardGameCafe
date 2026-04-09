import logging
from typing import Optional
import requests
from .vipps_config import VippsConfig
from .vipps_auth import VippsAuth

logger = logging.getLogger(__name__)


class VippsClient:
    def __init__(self, config: VippsConfig, session: Optional[requests.Session] = None):
        self.config = config
        # keep optional session param for future use, but use module requests for test patching
        self.session = session
        self.auth = VippsAuth(config, session=session)

    def _url(self, path: str) -> str:
        return f"{self.config.base_url}{path}"

    def initiate_payment(self, payload: dict) -> dict:
        url = self._url("/ecomm/v2/payments")
        headers = self.auth.auth_headers()
        # Use module-level requests.post so tests can patch `requests.post`
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_details(self, provider_ref: str) -> dict:
        url = self._url(f"/ecomm/v2/payments/{provider_ref}/details")
        headers = self.auth.auth_headers()
        # Use module-level requests.get so tests can patch `requests.get`
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def capture(self, provider_ref: str, payload: dict, idempotency_key: Optional[str] = None) -> requests.Response:
        url = self._url(f"/ecomm/v2/payments/{provider_ref}/capture")
        headers = self.auth.auth_headers()
        if idempotency_key:
            headers["X-Request-Id"] = idempotency_key
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        return resp

    def cancel(self, provider_ref: str, payload: dict, idempotency_key: Optional[str] = None) -> requests.Response:
        url = self._url(f"/ecomm/v2/payments/{provider_ref}/cancel")
        headers = self.auth.auth_headers()
        if idempotency_key:
            headers["X-Request-Id"] = idempotency_key
        resp = requests.put(url, json=payload, headers=headers, timeout=10)
        return resp

    def refund(self, provider_ref: str, payload: dict) -> requests.Response:
        url = self._url(f"/ecomm/v2/payments/{provider_ref}/refund")
        headers = self.auth.auth_headers()
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        return resp
