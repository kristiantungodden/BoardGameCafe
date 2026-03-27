from abc import ABC, abstractmethod
from features.payments.domain.models.payment import Payment


class PaymentRepositoryInterface(ABC):
    @abstractmethod
    def add(self, payment: Payment) -> Payment:
        raise NotImplementedError