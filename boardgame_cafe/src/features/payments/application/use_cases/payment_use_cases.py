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


def _resolve_billable_units(booking: BillableBooking) -> int:
    table_count = getattr(booking, "table_count", None)
    if table_count is None:
        table_count = getattr(booking, "party_size", None)

    if table_count is None:
        raise ValueError("Booking must define table_count or party_size for billing")

    return int(table_count)


def calculate_amount_cents(booking: BillableBooking) -> int:
    explicit_table_total = getattr(booking, "table_price_cents_total", None)
    explicit_game_total = int(getattr(booking, "game_price_cents_total", 0) or 0)
    explicit_base_fee = getattr(booking, "base_fee_cents", None)

    if explicit_table_total is not None:
        table_total = int(explicit_table_total)
    else:
        billable_units = _resolve_billable_units(booking)
        table_total = billable_units * PRICE_PER_CAPACITY_CENTS

    base_fee = int(PRICE_BASE_TABLE if explicit_base_fee is None else explicit_base_fee)
    return table_total + explicit_game_total + base_fee


def calculate_amount_kroner(booking: BillableBooking) -> float:
    return calculate_amount_cents(booking) / 100.0


def create_calculated_payment(booking: BillableBooking) -> Payment:
    if booking.id is None:
        raise ValueError("Reservation must have an id before payment can be calculated")
    if _resolve_billable_units(booking) <= 0:
        raise ValueError("table_count/party_size must be at least 1")

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