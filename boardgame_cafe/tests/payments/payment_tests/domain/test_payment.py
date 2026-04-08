import pytest

from features.payments.domain.models.payment import Payment, PaymentStatus


def test_payment_amount_kroner_converts_from_cents():
    payment = Payment(table_reservation_id=1, amount_cents=15000)

    assert payment.amount_kroner == 150.0


def test_payment_defaults_are_set():
    payment = Payment(table_reservation_id=1, amount_cents=15000)

    assert payment.id is None
    assert payment.currency == "NOK"
    assert payment.status == PaymentStatus.CALCULATED
    assert payment.provider == "none"
    assert payment.type == "reservation"
    assert payment.provider_ref == "not_created"


@pytest.mark.parametrize("reservation_id", [0, -1])
def test_payment_requires_positive_table_reservation_id(reservation_id):
    with pytest.raises(ValueError, match="table_reservation_id must be positive"):
        Payment(table_reservation_id=reservation_id, amount_cents=15000)


@pytest.mark.parametrize("amount_cents", [-1, -15000])
def test_payment_disallows_negative_amount(amount_cents):
    with pytest.raises(ValueError, match="amount_cents cannot be negative"):
        Payment(table_reservation_id=1, amount_cents=amount_cents)
