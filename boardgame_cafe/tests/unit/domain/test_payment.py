import pytest
from domain.models.payment import Payment


def test_payment_is_created():
    payment = Payment(
        table_reservation_id=1,
        amount_kroner=300.00,
    )

    assert payment.table_reservation_id == 1
    assert payment.amount_kroner == 300.00
    assert payment.currency == "NOK"
    assert payment.status == "calculated"


def test_payment_fails_for_negative_amount():
    with pytest.raises(ValueError):
        Payment(
            table_reservation_id=1,
            amount_kroner=-1.00,
        )