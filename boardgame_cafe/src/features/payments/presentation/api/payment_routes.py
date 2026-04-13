from http import HTTPStatus
from types import SimpleNamespace

from flask import Blueprint, jsonify, request

from features.payments.application.use_cases.payment_use_cases import (
    calculate_amount_cents,
    calculate_amount_kroner,
    create_calculated_payment,
    get_payment_by_id,
)
from features.payments.infrastructure.repositories.payment_repository import (
    PaymentRepository,
)
from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
)
from features.payments.domain.models.payment import PaymentStatus
from features.payments.presentation.schemas.payment_schema import PaymentSchema

payment_bp = Blueprint("payments", __name__, url_prefix="/api/payments")
_payment_repository: PaymentRepository | None = None
_payment_provider: PaymentProviderInterface | None = None


def configure_payment_routes(repository: PaymentRepository) -> None:
    global _payment_repository
    _payment_repository = repository


def configure_payment_provider(provider: PaymentProviderInterface) -> None:
    """Configure a payment provider adapter (e.g. Vipps)."""
    global _payment_provider
    _payment_provider = provider


@payment_bp.post("/calculate")
def calculate_payment_route():
    try:
        data = request.get_json(silent=True) or {}
        validated = PaymentSchema.validate_create_request(data)

        reservation = SimpleNamespace(
            id=validated["booking_id"],
            party_size=validated["party_size"],
        )
        payment = create_calculated_payment(reservation)

        return jsonify({
            **PaymentSchema.dump(payment),
            "party_size": validated["party_size"],
            "calculated_amount_cents": calculate_amount_cents(reservation),
            "calculated_amount_kroner": calculate_amount_kroner(reservation),
        }), HTTPStatus.OK
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


# CHANGE create_payment_route the same way — remove manual party_size checks:
@payment_bp.post("/")
def create_payment_route():
    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        data = request.get_json(silent=True) or {}
        validated = PaymentSchema.validate_create_request(data)

        reservation = SimpleNamespace(
            id=validated["booking_id"],
            party_size=validated["party_size"],
        )
        payment = create_calculated_payment(reservation)
        saved_payment = _payment_repository.add(payment)

        return jsonify(PaymentSchema.dump(saved_payment)), HTTPStatus.CREATED
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    

# ADD a GET endpoint at the bottom:
@payment_bp.get("/<int:payment_id>")
def get_payment_route(payment_id: int):
    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        return jsonify(PaymentSchema.dump(payment)), HTTPStatus.OK
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND


# Start a payment with the configured provider for an existing payment id
@payment_bp.post("/start/<int:payment_id>")
def start_payment_route(payment_id: int):
    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _payment_provider is None:
        return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        # Ask provider to start the payment and get provider reference
        provider_ref = _payment_provider.start_payment(payment)
        payment.provider = "vipps"
        payment.provider_ref = provider_ref
        payment.status = PaymentStatus.PENDING
        saved = _payment_repository.update(payment)
        return jsonify(PaymentSchema.dump(saved)), HTTPStatus.OK
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


# Check provider status for a stored payment and update local record
@payment_bp.get("/status/<int:payment_id>")
def check_payment_status_route(payment_id: int):
    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _payment_provider is None:
        return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        status = _payment_provider.fetch_status(payment.provider_ref)
        # Map provider status to domain PaymentStatus where appropriate
        if status == PaymentStatus.PAID:
            payment.status = PaymentStatus.PAID
        elif status == PaymentStatus.FAILED:
            payment.status = PaymentStatus.FAILED
        else:
            payment.status = PaymentStatus.PENDING

        saved = _payment_repository.update(payment)
        return jsonify(PaymentSchema.dump(saved)), HTTPStatus.OK
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


# Capture a reserved payment (optionally partial)
@payment_bp.post("/capture/<int:payment_id>")
def capture_payment_route(payment_id: int):
    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _payment_provider is None:
        return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        idempotency_key = request.headers.get("X-Request-Id")
        success = _payment_provider.capture(payment.provider_ref, payment.amount_cents, idempotency_key=idempotency_key)
        if success:
            payment.status = PaymentStatus.PAID
            saved = _payment_repository.update(payment)
            return jsonify(PaymentSchema.dump(saved)), HTTPStatus.OK
        return jsonify({"error": "capture failed"}), HTTPStatus.BAD_REQUEST
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST


# Cancel a payment reservation
@payment_bp.post("/cancel/<int:payment_id>")
def cancel_payment_route(payment_id: int):
    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _payment_provider is None:
        return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        idempotency_key = request.headers.get("X-Request-Id")
        success = _payment_provider.cancel(payment.provider_ref, should_release_remaining_funds=True, idempotency_key=idempotency_key)
        if success:
            payment.status = PaymentStatus.FAILED
            saved = _payment_repository.update(payment)
            return jsonify(PaymentSchema.dump(saved)), HTTPStatus.OK
        return jsonify({"error": "cancel failed"}), HTTPStatus.BAD_REQUEST
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST