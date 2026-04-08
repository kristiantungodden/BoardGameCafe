from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.domain.models.payment import (
    Payment,
    PRICE_PER_CAPACITY_CENTS,
    PRICE_BASE_TABLE,
)
from features.reservations.domain.models.reservation import TableReservation



def calculate_amount_cents(reservation: TableReservation) -> int:
    return (reservation.party_size * PRICE_PER_CAPACITY_CENTS) + PRICE_BASE_TABLE


def calculate_amount_kroner(reservation: TableReservation) -> float:
    return calculate_amount_cents(reservation) / 100.0


def create_calculated_payment(reservation: TableReservation) -> Payment:
    if reservation.id is None:
        raise ValueError("Reservation must have an id before payment can be calculated")

    amount_cents = calculate_amount_cents(reservation)

    return Payment(
        table_reservation_id=reservation.id,
        amount_cents=amount_cents,
    )

def create_and_save_payment(reservation: TableReservation, repository: PaymentRepositoryInterface) -> Payment:
    payment = create_calculated_payment(reservation)
    return repository.add(payment)