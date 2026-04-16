from abc import ABC, abstractmethod
from features.payments.domain.models.payment import Payment
from dataclasses import dataclass

@dataclass
class StartPaymentResult:
    provider_ref: str
    redirect_url: str | None = None
    provider_name: str = "unknown"

    def __str__(self) -> str:
        return self.provider_ref

    def __eq__(self, other) -> bool:
        if isinstance(other, str):
            return self.provider_ref == other
        if isinstance(other, StartPaymentResult):
            return (
                self.provider_ref == other.provider_ref
                and self.redirect_url == other.redirect_url
                and self.provider_name == other.provider_name
            )
        return False


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

    @abstractmethod
    def capture(self, provider_ref: str, amount_cents: int | None = None, idempotency_key: str | None = None) -> bool:
        """Capture (or partially capture) a reserved payment. Return True on success.

        Accept an optional `idempotency_key` which is sent as `X-Request-Id` to the
        provider for idempotent requests.
        """
        raise NotImplementedError

    @abstractmethod
    def cancel(self, provider_ref: str, should_release_remaining_funds: bool = False, idempotency_key: str | None = None) -> bool:
        """Cancel a payment reservation. Return True on success.

        Accept an optional `idempotency_key` sent as `X-Request-Id` when supported.
        """
        raise NotImplementedError
