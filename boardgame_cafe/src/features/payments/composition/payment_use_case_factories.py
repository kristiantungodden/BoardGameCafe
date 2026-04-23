from __future__ import annotations

import os
from typing import Any

from features.bookings.infrastructure.repositories.booking_repository import (
    SqlAlchemyBookingRepository,
)
from features.payments.application.services.payment_service import (
    PaymentApplicationService,
)
from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
)
from features.payments.infrastructure.repositories.payment_repository import (
    PaymentRepository,
)
from features.payments.infrastructure.stripe.stripe_adapter import StripeAdapter
from features.payments.application.services.booking_payment_lifecycle import (
    confirm_booking_after_success,
)
from shared.infrastructure.email.reservation_payment_publisher import (
    publish_reservation_payment_completed,
)


_payment_repo = PaymentRepository()
_booking_repo = SqlAlchemyBookingRepository()


def _create_payment_provider() -> PaymentProviderInterface:
    stripe_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not stripe_key:
        raise ValueError("STRIPE_SECRET_KEY environment variable is required")
    app_base_url = os.getenv("APP_BASE_URL") or "http://127.0.0.1:5000"
    return StripeAdapter(stripe_key, app_base_url)


def create_default_payment_provider() -> PaymentProviderInterface:
    return _create_payment_provider()


def _build_payment_service() -> PaymentApplicationService:
    return PaymentApplicationService(
        payment_repository=_payment_repo,
        payment_provider=_create_payment_provider(),
        booking_repository=_booking_repo,
    )


def _finalize_paid_payment(payment) -> None:
    if str(payment.status) != "paid":
        return

    resolved_booking_id, changed = confirm_booking_after_success(
        payment_id=payment.id,
        booking_id=payment.booking_id,
    )
    if changed and resolved_booking_id is not None:
        publish_reservation_payment_completed(resolved_booking_id)


def _sync_and_finalize_payment(payment_id: int, user: Any):
    payment_service = _build_payment_service()
    payment = payment_service.sync_payment_status(payment_id=payment_id, user=user)
    _finalize_paid_payment(payment)
    return payment


def get_payment_success_handler():
    def _finalize_payment(payment_id: int, user: Any):
        return _sync_and_finalize_payment(payment_id=payment_id, user=user)

    return _finalize_payment


def get_payment_status_handler():
    def _get_status(payment_id: int, user: Any):
        return _sync_and_finalize_payment(payment_id=payment_id, user=user)

    return _get_status


def get_payment_cancel_handler():
    def _get_payment(payment_id: int, user: Any):
        payment_service = _build_payment_service()
        return payment_service.get_payment(payment_id=payment_id, user=user)

    return _get_payment