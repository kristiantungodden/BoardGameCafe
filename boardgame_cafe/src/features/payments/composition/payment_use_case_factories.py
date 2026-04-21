from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
)


def create_default_payment_provider() -> PaymentProviderInterface:
    raise NotImplementedError("Payment provider must be configured in app initialization")