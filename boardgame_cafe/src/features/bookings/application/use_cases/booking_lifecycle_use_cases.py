from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional, Sequence

from features.bookings.application.interfaces.booking_repository_interface import (
    BookingRepositoryInterface,
)
from features.bookings.application.interfaces.booking_status_history_repository_interface import (
    BookingStatusHistoryRepositoryInterface,
)
from features.bookings.domain.models.booking import Booking
from features.bookings.domain.models.booking_status_history import (
    BookingStatusHistoryEntry,
)
from features.payments.application.interfaces.payment_provider_interface import (
    PaymentProviderInterface,
)
from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.domain.models.payment import PaymentStatus
from features.reservations.application.interfaces.table_reservation_repository_interface import (
    TableReservationRepositoryInterface,
)
from features.reservations.domain.models.table_reservation import TableReservation
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES
from shared.domain.exceptions import ValidationError
from shared.infrastructure import db

_OPENING_TIME = time(hour=9, minute=0)
_CLOSING_TIME = time(hour=23, minute=0)


def _is_slot_aligned(ts: datetime) -> bool:
    """Public booking API uses 30-minute slots; enforce strict time-window rules for those inputs."""
    return ts.minute in (0, 30) and ts.second == 0 and ts.microsecond == 0


@dataclass
class BookingCommand:
    customer_id: int
    table_id: int | None
    start_ts: datetime
    end_ts: datetime
    party_size: int
    notes: Optional[str] = None


class CreateBookingRecordUseCase:
    def __init__(
        self,
        booking_repo: BookingRepositoryInterface,
        table_reservation_repo: TableReservationRepositoryInterface,
        status_history_repo: Optional[BookingStatusHistoryRepositoryInterface] = None,
    ):
        self.booking_repo = booking_repo
        self.table_reservation_repo = table_reservation_repo
        self.status_history_repo = status_history_repo

    def execute(self, cmd: BookingCommand) -> Booking:
        if cmd.table_id is None:
            raise ValidationError("table_id must be selected before creating booking")

        enforce_time_window = _is_slot_aligned(cmd.start_ts) and _is_slot_aligned(cmd.end_ts)

        if enforce_time_window:
            if cmd.start_ts.date() != cmd.end_ts.date():
                raise ValidationError(
                    "Reservations must start and end on the same day (no overnight bookings)."
                )

            if cmd.start_ts.time() < _OPENING_TIME or cmd.end_ts.time() > _CLOSING_TIME:
                raise ValidationError(
                    "Reservations must be within opening hours: 09:00 to 23:00."
                )

        overlapping = self.booking_repo.find_overlapping_bookings(
            customer_id=cmd.customer_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
            statuses=OVERLAP_BLOCKING_STATUSES,
        )
        if overlapping:
            raise ValidationError(
                "Customer already has an active booking in the requested timeslot."
            )

        booking = Booking(
            customer_id=cmd.customer_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
            party_size=cmd.party_size,
            notes=cmd.notes,
        )
        booking = self.booking_repo.save(booking)

        self.table_reservation_repo.save(
            TableReservation(booking_id=booking.id, table_id=cmd.table_id)
        )

        if self.status_history_repo is not None:
            self.status_history_repo.save(
                BookingStatusHistoryEntry(
                    booking_id=booking.id,
                    from_status=None,
                    to_status=booking.status,
                    source="create",
                    actor_user_id=cmd.customer_id,
                    actor_role="customer",
                )
            )

        return booking


class ListBookingsUseCase:
    def __init__(self, booking_repo: BookingRepositoryInterface):
        self.booking_repo = booking_repo

    def execute(self) -> Sequence[Booking]:
        return self.booking_repo.list_all()


class GetBookingByIdUseCase:
    def __init__(self, booking_repo: BookingRepositoryInterface):
        self.booking_repo = booking_repo

    def execute(self, booking_id: int) -> Optional[Booking]:
        return self.booking_repo.get_by_id(booking_id)


class CancelBookingUseCase:
    def __init__(
        self,
        booking_repo: BookingRepositoryInterface,
        status_history_repo: Optional[BookingStatusHistoryRepositoryInterface] = None,
        payment_repo: Optional[PaymentRepositoryInterface] = None,
        payment_provider: Optional[PaymentProviderInterface] = None,
    ):
        self.booking_repo = booking_repo
        self.status_history_repo = status_history_repo
        self.payment_repo = payment_repo
        self.payment_provider = payment_provider

    def execute(
        self,
        booking_id: int,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
    ) -> Optional[Booking]:
        return _execute_transition_with_history(
            booking_repo=self.booking_repo,
            status_history_repo=self.status_history_repo,
            payment_repo=self.payment_repo,
            payment_provider=self.payment_provider,
            booking_id=booking_id,
            transition_method_name="cancel",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )


class SeatBookingUseCase:
    def __init__(
        self,
        booking_repo: BookingRepositoryInterface,
        status_history_repo: Optional[BookingStatusHistoryRepositoryInterface] = None,
    ):
        self.booking_repo = booking_repo
        self.status_history_repo = status_history_repo

    def execute(
        self,
        booking_id: int,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
    ) -> Optional[Booking]:
        return _execute_transition_with_history(
            booking_repo=self.booking_repo,
            status_history_repo=self.status_history_repo,
            payment_repo=None,
            payment_provider=None,
            booking_id=booking_id,
            transition_method_name="seat",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )


class CompleteBookingUseCase:
    def __init__(
        self,
        booking_repo: BookingRepositoryInterface,
        status_history_repo: Optional[BookingStatusHistoryRepositoryInterface] = None,
    ):
        self.booking_repo = booking_repo
        self.status_history_repo = status_history_repo

    def execute(
        self,
        booking_id: int,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
    ) -> Optional[Booking]:
        return _execute_transition_with_history(
            booking_repo=self.booking_repo,
            status_history_repo=self.status_history_repo,
            payment_repo=None,
            payment_provider=None,
            booking_id=booking_id,
            transition_method_name="complete",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )


class MarkBookingNoShowUseCase:
    def __init__(
        self,
        booking_repo: BookingRepositoryInterface,
        status_history_repo: Optional[BookingStatusHistoryRepositoryInterface] = None,
    ):
        self.booking_repo = booking_repo
        self.status_history_repo = status_history_repo

    def execute(
        self,
        booking_id: int,
        actor_user_id: Optional[int] = None,
        actor_role: Optional[str] = None,
    ) -> Optional[Booking]:
        return _execute_transition_with_history(
            booking_repo=self.booking_repo,
            status_history_repo=self.status_history_repo,
            payment_repo=None,
            payment_provider=None,
            booking_id=booking_id,
            transition_method_name="mark_no_show",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )


class ListBookingStatusHistoryUseCase:
    def __init__(self, status_history_repo: BookingStatusHistoryRepositoryInterface):
        self.status_history_repo = status_history_repo

    def execute(self, booking_id: int) -> Sequence[BookingStatusHistoryEntry]:
        return self.status_history_repo.list_for_booking(booking_id)


def _execute_transition_with_history(
    booking_repo: BookingRepositoryInterface,
    status_history_repo: Optional[BookingStatusHistoryRepositoryInterface],
    payment_repo: Optional[PaymentRepositoryInterface],
    payment_provider: Optional[PaymentProviderInterface],
    booking_id: int,
    transition_method_name: str,
    actor_user_id: Optional[int],
    actor_role: Optional[str],
) -> Optional[Booking]:
    try:
        session = db.session()
    except RuntimeError:
        return _apply_transition_and_log(
            booking_repo,
            status_history_repo,
            payment_repo,
            payment_provider,
            booking_id,
            transition_method_name,
            actor_user_id,
            actor_role,
        )

    tx_ctx = session.begin_nested() if session.in_transaction() else session.begin()
    with tx_ctx:
        transition_booking_repo = _instantiate_repo_in_transaction(booking_repo, session)
        transition_history_repo = _instantiate_repo_in_transaction(
            status_history_repo, session
        )
        transition_payment_repo = _instantiate_repo_in_transaction(payment_repo, session)
        return _apply_transition_and_log(
            transition_booking_repo,
            transition_history_repo,
            transition_payment_repo,
            payment_provider,
            booking_id,
            transition_method_name,
            actor_user_id,
            actor_role,
        )


def _instantiate_repo_in_transaction(repo, session):
    if repo is None:
        return None

    try:
        return repo.__class__(session=session, auto_commit=False)
    except TypeError:
        return repo


def _apply_transition_and_log(
    booking_repo,
    status_history_repo,
    payment_repo,
    payment_provider,
    booking_id: int,
    transition_method_name: str,
    actor_user_id: Optional[int],
    actor_role: Optional[str],
) -> Optional[Booking]:
    booking = booking_repo.get_by_id(booking_id)
    if booking is None:
        return None

    previous_status = booking.status
    if transition_method_name == "cancel":
        _validate_cancellation_window(booking.start_ts)

    getattr(booking, transition_method_name)()
    updated = booking_repo.update(booking)

    if transition_method_name == "cancel":
        _refund_paid_booking_if_supported(
            booking_id=updated.id,
            payment_repo=payment_repo,
            payment_provider=payment_provider,
        )

    if status_history_repo is not None:
        status_history_repo.save(
            BookingStatusHistoryEntry(
                booking_id=updated.id,
                from_status=previous_status,
                to_status=updated.status,
                source="status_transition",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
            )
        )

    return updated


def _refund_paid_booking_if_supported(
    booking_id: int,
    payment_repo,
    payment_provider,
) -> None:
    if payment_repo is None or payment_provider is None:
        return

    payment = payment_repo.get_by_booking_id(booking_id)
    if payment is None:
        return

    provider_name = (getattr(payment, "provider", "") or "").lower()
    provider_ref = (getattr(payment, "provider_ref", "") or "").strip()
    if provider_name != "stripe" or not provider_ref or provider_ref == "not_created":
        return

    if payment.status != PaymentStatus.PAID:
        return

    refunded = payment_provider.refund(provider_ref)
    if not refunded:
        raise ValidationError("Payment refund failed during cancellation")

    payment.status = PaymentStatus.REFUNDED
    if hasattr(payment_repo, "update"):
        payment_repo.update(payment)


def _validate_cancellation_window(start_ts: datetime) -> None:
    now = datetime.now(tz=start_ts.tzinfo) if start_ts.tzinfo else datetime.now()
    if start_ts - now < timedelta(hours=24):
        raise ValidationError(
            "Booking can only be cancelled at least 24 hours before start time"
        )
