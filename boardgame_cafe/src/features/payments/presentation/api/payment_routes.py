from http import HTTPStatus
from types import SimpleNamespace

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from features.bookings.application.interfaces.booking_repository_interface import (
    BookingRepositoryInterface,
)
from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.application.use_cases.payment_use_cases import (
    calculate_amount_cents,
    calculate_amount_kroner,
    create_calculated_payment,
    get_payment_by_id,
)
from features.payments.composition.payment_use_case_factories import (
    create_default_payment_provider,
    is_vipps_provider,
)
from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
)
from features.payments.domain.models.payment import PaymentStatus
from features.payments.presentation.schemas.payment_schema import PaymentSchema

payment_bp = Blueprint("payments", __name__, url_prefix="/api/payments")
_payment_repository: PaymentRepositoryInterface | None = None
_payment_provider: PaymentProviderInterface | None = None
_booking_repository: BookingRepositoryInterface | None = None


def configure_payment_routes(repository: PaymentRepositoryInterface) -> None:
    global _payment_repository
    _payment_repository = repository


def configure_booking_repository(repository: BookingRepositoryInterface) -> None:
    global _booking_repository
    _booking_repository = repository


def configure_payment_provider(provider: PaymentProviderInterface) -> None:
    """Configure a payment provider adapter (e.g. Vipps)."""
    global _payment_provider
    _payment_provider = provider


def _resolve_provider_for_payment(payment) -> PaymentProviderInterface | None:
    """Use Vipps adapter for Vipps-tagged payments, otherwise use configured default provider."""
    provider_name = (getattr(payment, "provider", "") or "").lower()
    provider_ref = getattr(payment, "provider_ref", "") or ""
    if provider_name == "vipps" or provider_ref.startswith("vipps:"):
        if is_vipps_provider(_payment_provider):
            return _payment_provider
        return create_default_payment_provider()
    return _payment_provider


def _is_staff_or_admin(user) -> bool:
    role = getattr(user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    return role in {"staff", "admin"} or bool(
        getattr(user, "is_staff", False) or getattr(user, "is_admin", False)
    )


def _require_authenticated():
    if not getattr(current_user, "is_authenticated", False):
        return {"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED
    return None


def _get_booking_for_payment(payment):
    if _booking_repository is None:
        return None
    booking_id = getattr(payment, "booking_id", None)
    if booking_id is None:
        return None
    return _booking_repository.get_by_id(int(booking_id))


def _require_payment_access(payment):
    if _is_staff_or_admin(current_user):
        return None

    booking = _get_booking_for_payment(payment)
    if booking is None:
        return {"error": "Payment not found"}, HTTPStatus.NOT_FOUND

    if getattr(booking, "customer_id", None) != getattr(current_user, "id", None):
        return {"error": "Unauthorized access to payment"}, HTTPStatus.FORBIDDEN

    return None


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
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _booking_repository is None:
        return jsonify({"error": "Booking repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        data = request.get_json(silent=True) or {}
        validated = PaymentSchema.validate_create_request(data)

        booking = _booking_repository.get_by_id(validated["booking_id"])
        if booking is None:
            return jsonify({"error": "Reservation not found"}), HTTPStatus.NOT_FOUND
        if not _is_staff_or_admin(current_user) and getattr(booking, "customer_id", None) != getattr(current_user, "id", None):
            return jsonify({"error": "Unauthorized access to payment"}), HTTPStatus.FORBIDDEN

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
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        access_error = _require_payment_access(payment)
        if access_error:
            return access_error
        return jsonify(PaymentSchema.dump(payment)), HTTPStatus.OK
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND


# Start a payment with the configured provider for an existing payment id
@payment_bp.post("/start/<int:payment_id>")
def start_payment_route(payment_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _payment_provider is None:
        return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        access_error = _require_payment_access(payment)
        if access_error:
            return access_error
        provider = _resolve_provider_for_payment(payment)
        if provider is None:
            return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
        # Ask provider to start the payment and get provider reference
        result = provider.start_payment(payment)

        payment.provider = result.provider_name
        payment.provider_ref = result.provider_ref
        payment.status = PaymentStatus.PENDING

        saved = _payment_repository.update(payment)

        return jsonify({
            # Backward-compatible top-level fields used by existing Vipps tests.
            "provider": saved.provider,
            "provider_ref": saved.provider_ref,
            "status": saved.status.value if hasattr(saved.status, "value") else str(saved.status),
            "payment": PaymentSchema.dump(saved),
            "redirect_url": result.redirect_url,
        }), HTTPStatus.OK
    
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        current_app.logger.exception("Failed to start payment %s", payment_id)
        return jsonify({"error": f"Failed to start payment: {exc}"}), HTTPStatus.INTERNAL_SERVER_ERROR


# Check provider status for a stored payment and update local record
@payment_bp.get("/status/<int:payment_id>")
def check_payment_status_route(payment_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _payment_provider is None:
        return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        access_error = _require_payment_access(payment)
        if access_error:
            return access_error
        provider = _resolve_provider_for_payment(payment)
        if provider is None:
            return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
        status = provider.fetch_status(payment.provider_ref)
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
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _payment_provider is None:
        return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        access_error = _require_payment_access(payment)
        if access_error:
            return access_error
        provider = _resolve_provider_for_payment(payment)
        if provider is None:
            return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
        idempotency_key = request.headers.get("X-Request-Id")
        success = provider.capture(payment.provider_ref, payment.amount_cents, idempotency_key=idempotency_key)
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
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if _payment_repository is None:
        return jsonify({"error": "Payment repository is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
    if _payment_provider is None:
        return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR

    try:
        payment = get_payment_by_id(payment_id, _payment_repository)
        access_error = _require_payment_access(payment)
        if access_error:
            return access_error
        provider = _resolve_provider_for_payment(payment)
        if provider is None:
            return jsonify({"error": "Payment provider is not configured"}), HTTPStatus.INTERNAL_SERVER_ERROR
        idempotency_key = request.headers.get("X-Request-Id")
        success = provider.cancel(payment.provider_ref, should_release_remaining_funds=True, idempotency_key=idempotency_key)
        if success:
            payment.status = PaymentStatus.FAILED
            saved = _payment_repository.update(payment)
            return jsonify(PaymentSchema.dump(saved)), HTTPStatus.OK
        return jsonify({"error": "cancel failed"}), HTTPStatus.BAD_REQUEST
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST