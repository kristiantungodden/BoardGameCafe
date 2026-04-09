from typing import Literal

import pytest

from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.presentation.schemas.payment_schema import PaymentSchema


def test_validate_create_request_accepts_valid_payload():
    payload = {"booking_id": 10, "party_size": 4}

    validated = PaymentSchema.validate_create_request(payload)

    assert validated["booking_id"] == 10
    assert validated["party_size"] == 4


@pytest.mark.parametrize(
    "payload, message",
    [
        (None, "Request body must be a JSON object"),
        ({}, "booking_id is required"),
        ({"booking_id": "10"}, "booking_id must be an integer"),
        ({"booking_id": 0}, "booking_id must be positive"),
        ({"booking_id": 1}, "party_size is required"),
        ({"booking_id": 1, "party_size": "4"}, "party_size must be an integer"),
        ({"booking_id": 1, "party_size": 0}, "party_size must be at least 1"),
        ({"booking_id": 1, "party_size": -1}, "party_size must be at least 1"),
    ],
)
def test_validate_create_request_rejects_invalid_payload(payload: None | dict[str, str] | dict[str, int], message: Literal['Request body must be a JSON object'] | Literal['booking_id is required'] | Literal['booking_id must be an integer'] | Literal['booking_id must be positive'] | Literal['party_size is required'] | Literal['party_size must be an integer'] | Literal['party_size must be at least 1']):
    with pytest.raises(ValueError, match=message):
        PaymentSchema.validate_create_request(payload)


def test_dump_serializes_payment():
    payment = Payment(
        id=1,
        booking_id=7,
        amount_cents=32500,
        currency="NOK",
        status=PaymentStatus.CALCULATED,
        provider="none",
        type="reservation",
        provider_ref="not_created",
    )

    result = PaymentSchema.dump(payment)

    assert result == {
        "id": 1,
        "booking_id": 7,
        "amount_cents": 32500,
        "amount_kroner": 325.0,
        "currency": "NOK",
        "status": "calculated",
        "provider": "none",
        "type": "reservation",
        "provider_ref": "not_created",
        "created_at": None,
    }


def test_dump_many_serializes_multiple_payments():
    payments = [
        Payment(id=1, booking_id=1, amount_cents=17500),
        Payment(id=2, booking_id=2, amount_cents=32500),
    ]

    result = PaymentSchema.dump_many(payments)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2
    assert result[1]["amount_kroner"] == 325.0
