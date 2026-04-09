import pytest

from features.payments.application.use_cases.payment_use_cases import (
    PRICE_PER_CAPACITY_CENTS,
    PRICE_BASE_TABLE,
    calculate_amount_cents,
    calculate_amount_kroner,
    create_and_save_payment,
    create_calculated_payment,
)
from features.payments.domain.models.payment import Payment, PaymentStatus
from types import SimpleNamespace


class SpyPaymentRepository:
    def __init__(self):
        self.add_calls = []

    def add(self, payment: Payment) -> Payment:
        self.add_calls.append(payment)
        return Payment(
            id=99,
            booking_id=payment.booking_id,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            status=payment.status,
            provider=payment.provider,
            type=payment.type,
            provider_ref=payment.provider_ref,
        )


def test_calculate_amount_cents_returns_price_per_person_times_party_size():
    reservation = SimpleNamespace(id=1, party_size=4)

    result = calculate_amount_cents(reservation)

    assert result == 4 * PRICE_PER_CAPACITY_CENTS + PRICE_BASE_TABLE


def test_calculate_amount_kroner_returns_kroner_value():
    reservation = SimpleNamespace(id=1, party_size=3)

    result = calculate_amount_kroner(reservation)

    assert result == 475.0


def test_create_calculated_payment_builds_payment_from_reservation():
    reservation = SimpleNamespace(id=7, party_size=2)

    payment = create_calculated_payment(reservation)

    assert payment.id is None
    assert payment.booking_id == 7
    assert payment.amount_cents == 2 * PRICE_PER_CAPACITY_CENTS + PRICE_BASE_TABLE
    assert payment.currency == "NOK"
    assert payment.status == PaymentStatus.CALCULATED


def test_create_calculated_payment_raises_when_reservation_has_no_id():
    reservation = SimpleNamespace(id=None, party_size=2)

    with pytest.raises(ValueError, match="Reservation must have an id"):
        create_calculated_payment(reservation)


def test_create_and_save_payment_creates_payment_and_calls_repository():
    reservation = SimpleNamespace(id=12, party_size=5)
    repository = SpyPaymentRepository()

    saved_payment = create_and_save_payment(reservation, repository)

    assert len(repository.add_calls) == 1
    added_payment = repository.add_calls[0]
    assert added_payment.booking_id == 12
    assert added_payment.amount_cents == 5 * PRICE_PER_CAPACITY_CENTS + PRICE_BASE_TABLE
    assert saved_payment.id == 99
    assert saved_payment.amount_cents == 5 * PRICE_PER_CAPACITY_CENTS + PRICE_BASE_TABLE
