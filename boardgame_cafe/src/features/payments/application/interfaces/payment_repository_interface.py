from abc import ABC, abstractmethod
from features.payments.domain.models.payment import Payment


class PaymentRepositoryInterface(ABC):
    @abstractmethod
    def add(self, payment: Payment) -> Payment:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, payment_id: int) -> Payment | None:
        raise NotImplementedError
    
    @abstractmethod
    def get_by_booking_id(self, booking_id: int) -> Payment | None:
        raise NotImplementedError
