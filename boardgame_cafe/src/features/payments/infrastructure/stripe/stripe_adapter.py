import stripe
from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
    StartPaymentResult,
)
from features.payments.domain.models.payment import Payment


class StripeAdapter(PaymentProviderInterface):
    def __init__(self, api_key: str, app_base_url: str):
        if not api_key:
            raise ValueError("Missing STRIPE_SECRET_KEY")
        if not app_base_url:
            raise ValueError("Missing APP_BASE_URL")
        stripe.api_key = api_key
        self.app_base_url = app_base_url.rstrip("/")

    def start_payment(self, payment: Payment) -> StartPaymentResult:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": payment.currency.lower(),
                        "product_data": {
                            "name": f"Reservation {payment.booking_id}",
                        },
                        "unit_amount": payment.amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            metadata={
                "payment_id": str(payment.id),
            },
            success_url=f"{self.app_base_url}/payments/success/{payment.id}",
            cancel_url=f"{self.app_base_url}/payments/cancel/{payment.id}",
        )

        return StartPaymentResult(
            provider_ref=session.id,
            redirect_url=session.url,
            provider_name="stripe",
        )

    def fetch_status(self, provider_ref: str) -> str:
        session = stripe.checkout.Session.retrieve(provider_ref)
        if session.payment_status == "paid":
            return "paid"
        return "pending"

    def refund(self, provider_ref: str) -> bool:
        session = stripe.checkout.Session.retrieve(provider_ref)
        payment_intent = getattr(session, "payment_intent", None)
        if not payment_intent:
            return False

        if hasattr(payment_intent, "id"):
            payment_intent = payment_intent.id

        refund = stripe.Refund.create(payment_intent=payment_intent)
        return getattr(refund, "status", "") in {"succeeded", "pending"}