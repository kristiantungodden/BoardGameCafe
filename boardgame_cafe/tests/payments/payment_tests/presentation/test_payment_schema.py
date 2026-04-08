import pytest

from features.payments.domain.models.payment import Payment
from features.payments.presentation.schemas.payment_schema import PaymentSchema


def test_validate_create_request_accepts_valid_payload():
    payload = {"table_reservation_id": 10}

    validated = PaymentSchema.validate_create_request(payload)

    assert validated == {"table_reservation_id": 10}


@pytest.mark.parametrize(
    "payload, message",
    [
        (None, "Request body must be a JSON object"),
        ({}, "table_reservation_id is required"),
        ({"table_reservation_id": "10"}, "table_reservation_id must be an integer"),
        ({"table_reservation_id": 0}, "table_reservation_id must be positive"),
    ],
)
def test_validate_create_request_rejects_invalid_payload(payload, message):
    with pytest.raises(ValueError, match=message):
        PaymentSchema.validate_create_request(payload)


def test_dump_serializes_payment():
    payment = Payment(
        id=1,
        table_reservation_id=7,
        amount_cents=30000,
        currency="NOK",
        status="calculated",
        provider="none",
        type="reservation",
        provider_ref="not_created",
    )

    result = PaymentSchema.dump(payment)

    assert result == {
        "id": 1,
        "table_reservation_id": 7,
        "amount_cents": 30000,
        "amount_kroner": 300.0,
        "currency": "NOK",
        "status": "calculated",
        "provider": "none",
        "type": "reservation",
        "provider_ref": "not_created",
    }


def test_dump_many_serializes_multiple_payments():
    payments = [
        Payment(id=1, table_reservation_id=1, amount_cents=15000),
        Payment(id=2, table_reservation_id=2, amount_cents=30000),
    ]

    result = PaymentSchema.dump_many(payments)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2
    assert result[1]["amount_kroner"] == 300.0
