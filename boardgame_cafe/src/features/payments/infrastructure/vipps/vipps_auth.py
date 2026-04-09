import logging
from typing import Optional
import requests
from .vipps_config import VippsConfig

logger = logging.getLogger(__name__)


class VippsAuth:
    def __init__(self, config: VippsConfig, session: Optional[requests.Session] = None):
        self.config = config
        self._token: Optional[str] = None
        self._session = session or requests.Session()

    def _token_endpoint(self) -> str:
        return f"{self.config.base_url}/accesstoken/get"

    def get_access_token(self) -> str:
        if self._token:
            return self._token

        if not (self.config.client_id and self.config.client_secret):
            raise RuntimeError("Vipps client credentials not configured")

        headers = {"client_id": self.config.client_id, "client_secret": self.config.client_secret}
        if self.config.subscription_key:
            headers["Ocp-Apim-Subscription-Key"] = self.config.subscription_key

        # Use module-level requests.post so tests that patch `requests.post` work
        resp = requests.post(self._token_endpoint(), headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("Vipps token response missing access_token")
        self._token = token
        logger.debug("Vipps access token obtained")
        return token

    def auth_headers(self) -> dict:
        token = self.get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if self.config.subscription_key:
            headers["Ocp-Apim-Subscription-Key"] = self.config.subscription_key
        if self.config.merchant_serial_number:
            headers["Merchant-Serial-Number"] = str(self.config.merchant_serial_number)
        return headers
