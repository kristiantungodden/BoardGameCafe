import pytest
from features.payments.domain.models.payment import Payment, PaymentStatus


def test_payment_is_created():
    payment = Payment(
        booking_id=1,
        amount_cents=32500,
    )

    assert payment.booking_id == 1
    assert payment.amount_cents == 32500
    assert payment.currency == "NOK"
    assert payment.status == PaymentStatus.CALCULATED


def test_payment_fails_for_negative_amount():
    with pytest.raises(ValueError):
        Payment(
            booking_id=1,
            amount_cents=-1,
        )