from typing import Protocol

from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.domain.models.payment import (
    Payment,
    PRICE_PER_CAPACITY_CENTS,
    PRICE_BASE_TABLE,
)


class BillableBooking(Protocol):
    id: int | None
    party_size: int


def calculate_amount_cents(booking: BillableBooking) -> int:
    return (booking.party_size * PRICE_PER_CAPACITY_CENTS) + PRICE_BASE_TABLE


def calculate_amount_kroner(booking: BillableBooking) -> float:
    return calculate_amount_cents(booking) / 100.0


def create_calculated_payment(booking: BillableBooking) -> Payment:
    if booking.id is None:
        raise ValueError("Reservation must have an id before payment can be calculated")
    if booking.party_size <= 0:
        raise ValueError("party_size must be at least 1")

    amount_cents = calculate_amount_cents(booking)
    return Payment(
        booking_id=booking.id,
        amount_cents=amount_cents,
    )


def create_and_save_payment(booking: BillableBooking, repository: PaymentRepositoryInterface) -> Payment:
    payment = create_calculated_payment(booking)
    return repository.add(payment)

def get_payment_by_id(payment_id: int, repository: PaymentRepositoryInterface) -> Payment:
    payment = repository.get_by_id(payment_id)
    if payment is None:
        raise ValueError(f"Payment with id {payment_id} not found")
    return payment