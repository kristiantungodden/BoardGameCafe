from domain.models.payment import Payment
from domain.models.reservation import TableReservation

PRICE_PER_PERSON_CENTS = 15000  # 150 kr


def calculate_amount_cents(reservation: TableReservation) -> int:
    return reservation.party_size * PRICE_PER_PERSON_CENTS


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