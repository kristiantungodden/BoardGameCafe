from types import SimpleNamespace
from typing import Any

from features.bookings.application.interfaces.booking_repository_interface import (
    BookingRepositoryInterface,
)
from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
    StartPaymentResult,
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
from features.payments.domain.models.payment import Payment, PaymentStatus


class PaymentNotFoundError(ValueError):
    pass


class PaymentAccessDeniedError(PermissionError):
    pass


class PaymentApplicationService:
    def __init__(
        self,
        payment_repository: PaymentRepositoryInterface,
        payment_provider: PaymentProviderInterface,
        booking_repository: BookingRepositoryInterface,
    ):
        self.payment_repository = payment_repository
        self.payment_provider = payment_provider
        self.booking_repository = booking_repository

    @staticmethod
    def _is_staff_or_admin(user: Any) -> bool:
        role = getattr(user, "role", None)
        if hasattr(role, "value"):
            role = role.value
        return role in {"staff", "admin"} or bool(
            getattr(user, "is_staff", False) or getattr(user, "is_admin", False)
        )

    def _require_payment_access(self, payment: Payment, user: Any) -> None:
        if self._is_staff_or_admin(user):
            return

        booking = self.booking_repository.get_by_id(int(payment.booking_id))
        if booking is None:
            raise PaymentNotFoundError("Payment not found")

        if getattr(booking, "customer_id", None) != getattr(user, "id", None):
            raise PaymentAccessDeniedError("Unauthorized access to payment")

    def calculate_payment(self, booking_id: int, party_size: int) -> dict[str, Any]:
        reservation = SimpleNamespace(id=booking_id, party_size=party_size)
        payment = create_calculated_payment(reservation)
        return {
            "payment": payment,
            "party_size": party_size,
            "calculated_amount_cents": calculate_amount_cents(reservation),
            "calculated_amount_kroner": calculate_amount_kroner(reservation),
        }

    def create_payment(self, booking_id: int, party_size: int, user: Any) -> Payment:
        booking = self.booking_repository.get_by_id(booking_id)
        if booking is None:
            raise PaymentNotFoundError("Reservation not found")

        if not self._is_staff_or_admin(user) and getattr(booking, "customer_id", None) != getattr(
            user, "id", None
        ):
            raise PaymentAccessDeniedError("Unauthorized access to payment")

        calculated = self.calculate_payment(booking_id=booking_id, party_size=party_size)
        return self.payment_repository.add(calculated["payment"])

    def get_payment(self, payment_id: int, user: Any) -> Payment:
        try:
            payment = get_payment_by_id(payment_id, self.payment_repository)
        except ValueError as exc:
            raise PaymentNotFoundError(str(exc)) from exc

        self._require_payment_access(payment, user)
        return payment

    def start_payment(self, payment_id: int, user: Any) -> tuple[Payment, StartPaymentResult]:
        payment = self.get_payment(payment_id, user)
        result = self.payment_provider.start_payment(payment)

        payment.provider = result.provider_name
        payment.provider_ref = result.provider_ref
        payment.status = PaymentStatus.PENDING

        saved = self.payment_repository.update(payment)
        return saved, result

    def sync_payment_status(self, payment_id: int, user: Any) -> Payment:
        payment = self.get_payment(payment_id, user)
        status = self.payment_provider.fetch_status(payment.provider_ref)

        if status == PaymentStatus.PAID:
            payment.status = PaymentStatus.PAID
        elif status == PaymentStatus.FAILED:
            payment.status = PaymentStatus.FAILED
        else:
            payment.status = PaymentStatus.PENDING

        return self.payment_repository.update(payment)
