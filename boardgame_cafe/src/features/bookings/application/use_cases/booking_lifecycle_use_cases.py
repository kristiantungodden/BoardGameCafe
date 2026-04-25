from dataclasses import dataclass
from datetime import datetime, time, timedelta
from contextlib import nullcontext
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
from features.tables.application.interfaces.table_repository import (
    TableRepository as TableRepositoryInterface,
)
from shared.domain.datetime_utils import to_app_local
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES
from shared.domain.exceptions import ValidationError

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
            start_local = to_app_local(cmd.start_ts)
            end_local = to_app_local(cmd.end_ts)

            if start_local.date() != end_local.date():
                raise ValidationError(
                    "Reservations must start and end on the same day (no overnight bookings)."
                )

            if start_local.time() < _OPENING_TIME or end_local.time() > _CLOSING_TIME:
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
        table_reservation_repo: Optional[TableReservationRepositoryInterface] = None,
        table_repo: Optional[TableRepositoryInterface] = None,
    ):
        self.booking_repo = booking_repo
        self.status_history_repo = status_history_repo
        self.table_reservation_repo = table_reservation_repo
        self.table_repo = table_repo

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
            table_reservation_repo=self.table_reservation_repo,
            table_repo=self.table_repo,
        )


class CompleteBookingUseCase:
    def __init__(
        self,
        booking_repo: BookingRepositoryInterface,
        status_history_repo: Optional[BookingStatusHistoryRepositoryInterface] = None,
        table_reservation_repo: Optional[TableReservationRepositoryInterface] = None,
        table_repo: Optional[TableRepositoryInterface] = None,
    ):
        self.booking_repo = booking_repo
        self.status_history_repo = status_history_repo
        self.table_reservation_repo = table_reservation_repo
        self.table_repo = table_repo

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
            table_reservation_repo=self.table_reservation_repo,
            table_repo=self.table_repo,
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
    table_reservation_repo: Optional[TableReservationRepositoryInterface] = None,
    table_repo: Optional[TableRepositoryInterface] = None,
) -> Optional[Booking]:
    return _apply_transition_and_log(
        booking_repo,
        status_history_repo,
        payment_repo,
        payment_provider,
        booking_id,
        transition_method_name,
        actor_user_id,
        actor_role,
        table_reservation_repo,
        table_repo,
    )


def _apply_transition_and_log(
    booking_repo,
    status_history_repo,
    payment_repo,
    payment_provider,
    booking_id: int,
    transition_method_name: str,
    actor_user_id: Optional[int],
    actor_role: Optional[str],
    table_reservation_repo=None,
    table_repo=None,
) -> Optional[Booking]:
    session = _resolve_shared_session(
        booking_repo,
        status_history_repo,
        payment_repo,
        table_reservation_repo,
        table_repo,
    )
    auto_commit_repos = [
        repo
        for repo in (
            booking_repo,
            status_history_repo,
            payment_repo,
            table_reservation_repo,
            table_repo,
        )
        if _normalize_session(getattr(repo, "session", None)) is session and hasattr(repo, "auto_commit")
    ]

    tx_ctx = (
        session.begin_nested() if session is not None and session.in_transaction() else session.begin()
        if session is not None
        else nullcontext()
    )

    previous_auto_commit = []
    try:
        for repo in auto_commit_repos:
            previous_auto_commit.append((repo, repo.auto_commit))
            repo.auto_commit = False

        with tx_ctx:
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

            if transition_method_name == "seat":
                _sync_table_status_for_booking(
                    booking_id=updated.id,
                    table_reservation_repo=table_reservation_repo,
                    table_repo=table_repo,
                    target_status="occupied",
                )

            if transition_method_name == "complete":
                _sync_table_status_for_booking(
                    booking_id=updated.id,
                    table_reservation_repo=table_reservation_repo,
                    table_repo=table_repo,
                    target_status="available",
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
    finally:
        for repo, auto_commit in reversed(previous_auto_commit):
            repo.auto_commit = auto_commit


def _resolve_shared_session(*repos):
    sessions = [
        _normalize_session(getattr(repo, "session", None))
        for repo in repos
        if getattr(repo, "session", None) is not None
    ]
    if not sessions:
        return None

    first_session = sessions[0]
    if any(session is not first_session for session in sessions[1:]):
        return None

    return first_session


def _normalize_session(session):
    if session is None:
        return None

    if hasattr(session, "in_transaction"):
        return session

    if callable(session):
        resolved = session()
        if hasattr(resolved, "in_transaction"):
            return resolved

    return session


def _sync_table_status_for_booking(
    booking_id: int,
    table_reservation_repo,
    table_repo,
    target_status: str,
) -> None:
    if table_reservation_repo is None or table_repo is None:
        return

    table_links = table_reservation_repo.list_by_booking_id(booking_id)
    for link in table_links:
        table = table_repo.get_by_id(link.table_id)
        if table is None or table.status == target_status:
            continue

        if target_status == "occupied":
            table.occupy()
        elif target_status == "available":
            table.free()
        else:
            raise ValueError(f"Unsupported table status sync target '{target_status}'")

        table_repo.update(table)


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
