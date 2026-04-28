from __future__ import annotations

from features.bookings.application.interfaces.booking_repository_interface import (
    BookingRepositoryInterface,
)
from features.bookings.application.interfaces.booking_status_history_repository_interface import (
    BookingStatusHistoryRepositoryInterface,
)
from features.bookings.domain.models.booking_status_history import BookingStatusHistoryEntry
from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.domain.models.payment import PaymentStatus
from features.reservations.application.interfaces.game_reservation_repository_interface import (
    GameReservationRepositoryInterface,
)
from features.reservations.application.interfaces.reservation_qr_repository_interface import (
    ReservationQRCodeRepositoryInterface,
)
from features.reservations.application.interfaces.table_reservation_repository_interface import (
    TableReservationRepositoryInterface,
)


def _resolve_booking_id(
    payment_repo: PaymentRepositoryInterface,
    payment_id: int | None,
    booking_id: int | None,
) -> int | None:
    if booking_id is not None:
        return booking_id

    if payment_id is None:
        return None

    payment = payment_repo.get_by_id(payment_id)
    if payment is None:
        return None
    return int(payment.booking_id)


def confirm_booking_after_success(
    *,
    payment_repo: PaymentRepositoryInterface,
    booking_repo: BookingRepositoryInterface,
    status_history_repo: BookingStatusHistoryRepositoryInterface,
    payment_id: int | None = None,
    booking_id: int | None = None,
) -> tuple[int | None, bool]:
    """Mark payment paid and transition booking created -> confirmed.

    Returns (resolved_booking_id, changed).
    """
    resolved_booking_id = _resolve_booking_id(payment_repo, payment_id, booking_id)
    if resolved_booking_id is None:
        return None, False

    changed = False

    if payment_id is not None:
        payment = payment_repo.get_by_id(payment_id)
        if payment is not None and payment.status != PaymentStatus.PAID:
            payment.status = PaymentStatus.PAID
            payment_repo.update(payment)
            changed = True

    booking = booking_repo.get_by_id(resolved_booking_id)
    if booking is None:
        return resolved_booking_id, changed

    if booking.status == "created":
        booking.status = "confirmed"
        booking_repo.update(booking)
        changed = True
        status_history_repo.save(
            BookingStatusHistoryEntry(
                booking_id=booking.id,
                from_status="created",
                to_status="confirmed",
                source="payment_success",
            )
        )

    return resolved_booking_id, changed


def fail_payment_and_cleanup_created_booking(
    *,
    payment_repo: PaymentRepositoryInterface,
    booking_repo: BookingRepositoryInterface,
    status_history_repo: BookingStatusHistoryRepositoryInterface,
    table_reservation_repo: TableReservationRepositoryInterface,
    game_reservation_repo: GameReservationRepositoryInterface,
    reservation_qr_repo: ReservationQRCodeRepositoryInterface,
    payment_id: int | None = None,
    booking_id: int | None = None,
) -> tuple[int | None, bool]:
    """Mark payment failed and delete booking aggregate when still in created state.

    Returns (resolved_booking_id, deleted).
    """
    resolved_booking_id = _resolve_booking_id(payment_repo, payment_id, booking_id)
    if resolved_booking_id is None:
        return None, False

    payment = payment_repo.get_by_id(payment_id) if payment_id is not None else None
    if payment is not None and payment.status not in {PaymentStatus.PAID, PaymentStatus.FAILED}:
        payment.status = PaymentStatus.FAILED
        payment_repo.update(payment)

    booking = booking_repo.get_by_id(resolved_booking_id)
    if booking is None:
        return resolved_booking_id, False

    # Never delete successful bookings.
    if payment is not None and payment.status == PaymentStatus.PAID:
        return resolved_booking_id, False

    if booking.status != "created":
        return resolved_booking_id, False

    reservation_qr_repo.delete_for_reservation(resolved_booking_id)
    for reservation_game in list(game_reservation_repo.list_for_booking(resolved_booking_id)):
        game_reservation_repo.delete(reservation_game.id)
    for table_reservation in list(table_reservation_repo.list_by_booking_id(resolved_booking_id)):
        table_reservation_repo.delete(table_reservation.id)
    if payment is not None and payment.id is not None:
        payment_repo.delete(payment.id)
    elif payment_id is not None:
        payment_repo.delete(payment_id)
    status_history_repo.delete_for_booking(resolved_booking_id)
    booking_repo.delete(resolved_booking_id)

    return resolved_booking_id, True
