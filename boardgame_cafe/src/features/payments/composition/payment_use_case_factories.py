from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
)
from features.payments.infrastructure.vipps import VippsAdapter


def create_default_payment_provider() -> PaymentProviderInterface:
    return VippsAdapter()


def is_vipps_provider(provider: PaymentProviderInterface | None) -> bool:
    return isinstance(provider, VippsAdapter)