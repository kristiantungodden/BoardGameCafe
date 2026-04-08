import pytest
from datetime import datetime, timedelta

from features.payments.application.use_cases.payment_use_cases import (
    calculate_amount_kroner,
    create_calculated_payment,
)
from features.reservations.domain.models.reservation import TableReservation


def make_reservation(
    reservation_id=1,
    party_size=2,
):
    start = datetime.now() 
    end = start + timedelta(hours=2)

    return TableReservation(
        id=reservation_id,
        customer_id=1,
        table_id=1,
        start_ts=start,
        end_ts=end,
        party_size=party_size,
    )


def test_calculate_amount_kroner_uses_party_size():
    reservation = make_reservation(party_size=3)

    amount = calculate_amount_kroner(reservation)

    assert amount == 475.00


def test_create_calculated_payment_returns_payment():
    reservation = make_reservation(reservation_id=42, party_size=4)

    payment = create_calculated_payment(reservation)

    assert payment.table_reservation_id == 42
    assert payment.amount_kroner == 625.00
    assert payment.status == "calculated"


def test_create_calculated_payment_fails_without_reservation_id():
    reservation = make_reservation(reservation_id=None, party_size=2)

    with pytest.raises(ValueError):
        create_calculated_payment(reservation)