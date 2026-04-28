from abc import ABC, abstractmethod
from features.payments.domain.models.payment import Payment
from dataclasses import dataclass

@dataclass
class StartPaymentResult:
    provider_ref: str
    redirect_url: str | None = None
    provider_name: str = "unknown"



class PaymentProviderInterface(ABC):
    @abstractmethod
    def start_payment(self, payment: Payment) -> StartPaymentResult:
        """Start a payment with the provider and return a provider-specific reference/id."""
        raise NotImplementedError

    @abstractmethod
    def fetch_status(self, provider_ref: str) -> str:
        """Fetch payment status from provider. Return a provider-agnostic status string (e.g. 'pending','paid','failed')."""
        raise NotImplementedError

    @abstractmethod
    def refund(self, provider_ref: str) -> bool:
        """Request a refund for the given provider reference. Return True on success."""
        raise NotImplementedError
