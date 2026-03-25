from domain.models.payment import Payment
from domain.models.reservation import TableReservation

PRICE_PER_PERSON_KRONER = 150.00  # 150 kr


def calculate_amount_kroner(reservation: TableReservation) -> int:
    return reservation.party_size * PRICE_PER_PERSON_KRONER


def create_calculated_payment(reservation: TableReservation) -> Payment:
    if reservation.id is None:
        raise ValueError("Reservation must have an id before payment can be calculated")

    amount_kroner = calculate_amount_kroner(reservation)

    return Payment(
        table_reservation_id=reservation.id,
        amount_kroner=amount_kroner,
    )