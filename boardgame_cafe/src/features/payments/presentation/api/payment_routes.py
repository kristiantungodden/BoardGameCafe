from http import HTTPStatus
from types import SimpleNamespace

from flask import Blueprint, jsonify, request

from features.payments.application.use_cases.payment_use_cases import (
    calculate_amount_cents,
    calculate_amount_kroner,
    create_calculated_payment,
)
from features.payments.infrastructure.repositories.payment_repository import (
    PaymentRepository,
)
from features.payments.presentation.schemas.payment_schema import PaymentSchema

payment_bp = Blueprint("payments", __name__, url_prefix="/payments")
_payment_repository: PaymentRepository | None = None


def configure_payment_routes(repository: PaymentRepository) -> None:
    global _payment_repository
    _payment_repository = repository


@payment_bp.post("/calculate")
def calculate_payment_route():
    try:
        data = request.get_json(silent=True) or {}
        validated = PaymentSchema.validate_create_request(data)
        party_size = data.get("party_size")

        if not isinstance(party_size, int):
            raise ValueError("party_size is required and must be an integer")
        if party_size < 0:
            raise ValueError("party_size cannot be negative")

        reservation = SimpleNamespace(
            id=validated["table_reservation_id"],
            party_size=party_size,
        )
        payment = create_calculated_payment(reservation)

        return (
            jsonify(
                {
                    **PaymentSchema.dump(payment),
                    "party_size": party_size,
                    "calculated_amount_cents": calculate_amount_cents(reservation),
                    "calculated_amount_kroner": calculate_amount_kroner(reservation),
                }
            ),
            HTTPStatus.OK,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


@payment_bp.post("/")
def create_payment_route():
    if _payment_repository is None:
        return (
            jsonify({"error": "Payment repository is not configured"}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    try:
        data = request.get_json(silent=True) or {}
        validated = PaymentSchema.validate_create_request(data)
        party_size = data.get("party_size")

        if not isinstance(party_size, int):
            raise ValueError("party_size is required and must be an integer")
        if party_size < 0:
            raise ValueError("party_size cannot be negative")

        reservation = SimpleNamespace(
            id=validated["table_reservation_id"],
            party_size=party_size,
        )
        payment = create_calculated_payment(reservation)
        saved_payment = _payment_repository.add(payment)

        return jsonify(PaymentSchema.dump(saved_payment)), HTTPStatus.CREATED
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
