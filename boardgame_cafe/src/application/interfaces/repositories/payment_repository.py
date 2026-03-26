from abc import ABC, abstractmethod
from domain.models.payment import Payment


class PaymentRepository(ABC):
    @abstractmethod
    def add(self, payment: Payment) -> Payment:
        raise NotImplementedError