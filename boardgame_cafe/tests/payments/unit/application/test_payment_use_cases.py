import pytest
from datetime import datetime, timedelta

from features.payments.domain.models.payment import PaymentStatus
from features.payments.domain.services.payment_calculation import (
    calculate_amount_kroner,
    create_calculated_payment,
)
from features.bookings.domain.models.booking import Booking


def make_reservation(
    reservation_id=1,
    party_size=2,
    table_count=None,
):
    start = datetime.now() 
    end = start + timedelta(hours=2)

    reservation = Booking(
        id=reservation_id,
        customer_id=1,
        start_ts=start,
        end_ts=end,
        party_size=party_size,
    )
    setattr(reservation, "table_id", 1)
    if table_count is not None:
        setattr(reservation, "table_count", table_count)
    return reservation


def test_calculate_amount_kroner_prefers_table_count_when_present():
    reservation = make_reservation(party_size=8, table_count=3)

    amount = calculate_amount_kroner(reservation)

    assert amount == 475.00


def test_calculate_amount_kroner_falls_back_to_party_size_when_table_count_missing():
    reservation = make_reservation(party_size=3)

    amount = calculate_amount_kroner(reservation)

    assert amount == 475.00


def test_create_calculated_payment_returns_payment_for_table_count():
    reservation = make_reservation(reservation_id=42, party_size=4, table_count=2)

    payment = create_calculated_payment(reservation)

    assert payment.booking_id == 42
    assert payment.amount_kroner == 325.00
    assert payment.status == PaymentStatus.CALCULATED


def test_create_calculated_payment_fails_without_reservation_id():
    reservation = make_reservation(reservation_id=None, party_size=2)

    with pytest.raises(ValueError):
        create_calculated_payment(reservation)