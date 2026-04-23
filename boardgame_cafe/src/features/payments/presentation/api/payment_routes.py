from http import HTTPStatus

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from features.bookings.application.interfaces.booking_repository_interface import BookingRepositoryInterface
from features.payments.application.interfaces.payment_provider_interface import PaymentProviderInterface
from features.payments.application.interfaces.payment_repository_interface import PaymentRepositoryInterface
from features.payments.application.services.payment_service import (
    PaymentAccessDeniedError,
    PaymentApplicationService,
    PaymentNotFoundError,
)
from features.payments.composition.payment_use_case_factories import (
    get_payment_status_handler,
)
from features.payments.presentation.schemas.payment_schema import PaymentSchema

payment_bp = Blueprint("payments", __name__, url_prefix="/api/payments")
_payment_service: PaymentApplicationService | None = None
_pending_repository: PaymentRepositoryInterface | None = None
_pending_provider: PaymentProviderInterface | None = None
_pending_booking_repository: BookingRepositoryInterface | None = None


def _maybe_configure_from_pending() -> None:
    if (
        _pending_repository is not None
        and _pending_provider is not None
        and _pending_booking_repository is not None
    ):
        configure_payment_service(
            repository=_pending_repository,
            provider=_pending_provider,
            booking_repository=_pending_booking_repository,
        )


def configure_payment_service(
    repository: PaymentRepositoryInterface,
    provider: PaymentProviderInterface,
    booking_repository: BookingRepositoryInterface,
) -> None:
    global _payment_service
    _payment_service = PaymentApplicationService(
        payment_repository=repository,
        payment_provider=provider,
        booking_repository=booking_repository,
    )


def configure_payment_routes(repository: PaymentRepositoryInterface) -> None:
    global _pending_repository
    _pending_repository = repository
    _maybe_configure_from_pending()


def configure_booking_repository(repository: BookingRepositoryInterface) -> None:
    global _pending_booking_repository
    _pending_booking_repository = repository
    _maybe_configure_from_pending()


def configure_payment_provider(provider: PaymentProviderInterface) -> None:
    global _pending_provider
    _pending_provider = provider
    _maybe_configure_from_pending()


def _require_authenticated():
    if not getattr(current_user, "is_authenticated", False):
        return {"error": "Authentication required"}, HTTPStatus.UNAUTHORIZED
    return None


def _validate_create_request(data: dict) -> tuple[dict | None, dict | None]:
    try:
        validated = PaymentSchema.validate_create_request(data)
        return None, validated
    except ValueError as exc:
        return (jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST), None


def _require_service() -> PaymentApplicationService:
    if _payment_service is None:
        raise RuntimeError("Payment service is not configured")
    return _payment_service


@payment_bp.post("/calculate")
def calculate_payment_route():
    data = request.get_json(silent=True) or {}
    error_response, validated = _validate_create_request(data)
    if error_response:
        return error_response

    try:
        result = _require_service().calculate_payment(
            booking_id=validated["booking_id"],
            party_size=validated["party_size"],
        )
        return jsonify(
            {
                **PaymentSchema.dump(result["payment"]),
                "party_size": result["party_size"],
                "calculated_amount_cents": result["calculated_amount_cents"],
                "calculated_amount_kroner": result["calculated_amount_kroner"],
            }
        ), HTTPStatus.OK
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.INTERNAL_SERVER_ERROR


# Create a new payment and save to database
@payment_bp.post("/")
def create_payment_route():
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    error_response, validated = _validate_create_request(data)
    if error_response:
        return error_response

    try:
        saved_payment = _require_service().create_payment(
            booking_id=validated["booking_id"],
            party_size=validated["party_size"],
            user=current_user,
        )
        return jsonify(PaymentSchema.dump(saved_payment)), HTTPStatus.CREATED
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except PaymentNotFoundError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND
    except PaymentAccessDeniedError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.FORBIDDEN
    



# Get a payment by id
@payment_bp.get("/<int:payment_id>")
def get_payment_route(payment_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    try:
        payment = _require_service().get_payment(payment_id=payment_id, user=current_user)
        return jsonify(PaymentSchema.dump(payment)), HTTPStatus.OK
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except PaymentNotFoundError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND
    except PaymentAccessDeniedError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.FORBIDDEN


# Start a payment with Stripe for an existing payment
@payment_bp.post("/start/<int:payment_id>")
def start_payment_route(payment_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    try:
        saved, result = _require_service().start_payment(payment_id=payment_id, user=current_user)

        return jsonify({
            "provider": saved.provider,
            "provider_ref": saved.provider_ref,
            "status": saved.status.value if hasattr(saved.status, "value") else str(saved.status),
            "payment": PaymentSchema.dump(saved),
            "redirect_url": result.redirect_url,
        }), HTTPStatus.OK

    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except PaymentNotFoundError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND
    except PaymentAccessDeniedError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.FORBIDDEN
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        current_app.logger.exception("Failed to start payment %s", payment_id)
        return jsonify({"error": f"Failed to start payment: {exc}"}), HTTPStatus.INTERNAL_SERVER_ERROR


# Check payment status with Stripe
@payment_bp.get("/status/<int:payment_id>")
def check_payment_status_route(payment_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    try:
        saved = get_payment_status_handler()(payment_id, current_user)
        return jsonify(PaymentSchema.dump(saved)), HTTPStatus.OK
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.INTERNAL_SERVER_ERROR
    except PaymentNotFoundError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND
    except PaymentAccessDeniedError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.FORBIDDEN
    except ValueError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
