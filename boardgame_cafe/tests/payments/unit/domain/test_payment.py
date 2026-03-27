import pytest
from features.payments.domain.models.payment import Payment


def test_payment_is_created():
    payment = Payment(
        table_reservation_id=1,
        amount_cents=30000,
    )

    assert payment.table_reservation_id == 1
    assert payment.amount_cents == 30000
    assert payment.currency == "NOK"
    assert payment.status == "calculated"


def test_payment_fails_for_negative_amount():
    with pytest.raises(ValueError):
        Payment(
            table_reservation_id=1,
            amount_cents=-1,
        )