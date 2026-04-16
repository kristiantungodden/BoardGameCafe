import logging
from typing import Optional
from uuid import uuid4

import requests

from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
    StartPaymentResult,
)
from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.vipps.vipps_config import VippsConfig
from features.payments.infrastructure.vipps.vipps_client import VippsClient
from features.payments.infrastructure.vipps.vipps_mapper import map_vipps_status_to_payment_status

logger = logging.getLogger(__name__)


# Small provider DTOs / simple models kept here per request
class OrderDetails:
    def __init__(self, order_id: str, url: Optional[str] = None):
        self.order_id = order_id
        self.url = url


class VippsAdapter(PaymentProviderInterface):
    """Vipps adapter that composes client, config and mapper.

    This class maintains the previous public API (methods and names) so existing
    code can continue importing `VippsAdapter` from the package root.
    """

    def __init__(
        self,
        config: Optional[VippsConfig] = None,
        session: Optional[requests.Session] = None,
        # Backwards-compatible constructor params (some tests / callers pass these)
        base_url: Optional[str] = None,
        subscription_key: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        merchant_serial_number: Optional[str] = None,
        callback_prefix: Optional[str] = None,
    ):
        if config:
            self.config = config
        else:
            # If explicit params are provided, construct config from them, else read env
            if any((base_url, subscription_key, client_id, client_secret, merchant_serial_number, callback_prefix)):
                self.config = VippsConfig(
                    base_url=base_url or VippsConfig.from_env().base_url,
                    subscription_key=subscription_key,
                    client_id=client_id,
                    client_secret=client_secret,
                    merchant_serial_number=merchant_serial_number,
                    callback_prefix=callback_prefix,
                )
            else:
                self.config = VippsConfig.from_env()

        self.client = VippsClient(self.config, session=session)

    def _is_simulated(self) -> bool:
        return not (self.config.client_id and self.config.client_secret and self.config.subscription_key)

    def start_payment(self, payment: Payment) -> StartPaymentResult:
        booking_id = payment.booking_id
        if self._is_simulated():
            ref = f"vipps:{uuid4()}"
            logger.info("Simulated start_payment => %s", ref)
            return StartPaymentResult(
                provider_ref=ref,
                redirect_url=f"http://localhost:5000/mock-vipps/pay?ref={ref}&amount={payment.amount_cents}",
                provider_name="vipps",
            )
        

        order_id = f"bgc-{booking_id}-{payment.id or uuid4()}"
        payload = {
            "customerInfo": {},
            "merchantInfo": {
                "merchantSerialNumber": self.config.merchant_serial_number,
                "callbackPrefix": self.config.callback_prefix,
                "fallBack": "https://example.com/vipps/fallback",
            },
            "transaction": {
                "amount": payment.amount_cents,
                "orderId": order_id,
                "transactionText": f"Booking {booking_id}",
            },
        }
        data = self.client.initiate_payment(payload)
        return StartPaymentResult(
            provider_ref=data.get("orderId") or data.get("order_id"),
            redirect_url=data.get("url"),
            provider_name="vipps",
        )

    def fetch_status(self, provider_ref: str) -> PaymentStatus:
        if provider_ref.startswith("vipps:") and self._is_simulated():
            return PaymentStatus.PENDING

        details = self.client.get_details(provider_ref)

        tx_history = details.get("transactionLogHistory") or []
        latest = None
        if tx_history:
            latest = tx_history[0].get("transactionInfo")
        else:
            latest = details.get("transactionInfo") or (details.get("transaction") and details.get("transaction").get("transactionInfo"))

        status = None
        if latest and isinstance(latest, dict):
            status = latest.get("status")

        return map_vipps_status_to_payment_status(status)

    def refund(self, provider_ref: str, amount_cents: Optional[int] = None) -> bool:
        if provider_ref.startswith("vipps:") and self._is_simulated():
            logger.info("Simulated refund for %s", provider_ref)
            return True

        payload = {
            "merchantInfo": {"merchantSerialNumber": self.config.merchant_serial_number},
            "transaction": {"amount": amount_cents} if amount_cents is not None else {"amount": 0},
        }
        resp = self.client.refund(provider_ref, payload)
        if resp.status_code == 200:
            return True
        resp.raise_for_status()
        return False

    def capture(self, provider_ref: str, amount_cents: Optional[int] = None, idempotency_key: Optional[str] = None) -> bool:
        if provider_ref.startswith("vipps:") and self._is_simulated():
            logger.info("Simulated capture for %s", provider_ref)
            return True

        payload = {
            "merchantInfo": {"merchantSerialNumber": self.config.merchant_serial_number},
            "transaction": {"amount": amount_cents} if amount_cents is not None else {},
        }
        resp = self.client.capture(provider_ref, payload, idempotency_key=idempotency_key)
        if resp.status_code == 200:
            return True
        resp.raise_for_status()
        return False

    def cancel(self, provider_ref: str, should_release_remaining_funds: bool = False, idempotency_key: Optional[str] = None) -> bool:
        if provider_ref.startswith("vipps:") and self._is_simulated():
            logger.info("Simulated cancel for %s", provider_ref)
            return True

        payload = {
            "merchantInfo": {"merchantSerialNumber": self.config.merchant_serial_number},
            "transaction": {},
            "shouldReleaseRemainingFunds": should_release_remaining_funds,
        }
        resp = self.client.cancel(provider_ref, payload, idempotency_key=idempotency_key)
        if resp.status_code == 200:
            return True
        resp.raise_for_status()
        return False
