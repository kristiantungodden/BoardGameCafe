from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.domain.models.payment import Payment
from features.payments.domain.services.payment_calculation import (
    BillableBooking,
    create_calculated_payment,
)


def create_and_save_payment(booking: BillableBooking, repository: PaymentRepositoryInterface) -> Payment:
    payment = create_calculated_payment(booking)
    return repository.add(payment)


def get_payment_by_id(payment_id: int, repository: PaymentRepositoryInterface) -> Payment:
    payment = repository.get_by_id(payment_id)
    if payment is None:
        raise ValueError(f"Payment with id {payment_id} not found")
    return payment
