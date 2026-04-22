from __future__ import annotations

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.bookings.infrastructure.database.booking_status_history_db import (
    BookingStatusHistoryDB,
)
from features.payments.infrastructure.database.payments_db import PaymentDB
from features.reservations.infrastructure.database.game_reservations_db import GameReservationDB
from features.reservations.infrastructure.database.reservation_qr_codes_db import (
    ReservationQRCodeDB,
)
from features.reservations.infrastructure.database.table_reservations_db import (
    TableReservationDB,
)
from shared.infrastructure import db


def _resolve_booking_id(payment_id: int | None, booking_id: int | None) -> int | None:
    if booking_id is not None:
        return booking_id

    if payment_id is None:
        return None

    payment = db.session.get(PaymentDB, payment_id)
    if payment is None:
        return None
    return int(payment.booking_id)


def confirm_booking_after_success(
    *,
    payment_id: int | None = None,
    booking_id: int | None = None,
) -> tuple[int | None, bool]:
    """Mark payment paid and transition booking created -> confirmed.

    Returns (resolved_booking_id, changed).
    """
    resolved_booking_id = _resolve_booking_id(payment_id, booking_id)
    if resolved_booking_id is None:
        return None, False

    changed = False

    if payment_id is not None:
        payment = db.session.get(PaymentDB, payment_id)
        if payment is not None and payment.status != "paid":
            payment.status = "paid"
            changed = True

    booking = db.session.get(BookingDB, resolved_booking_id)
    if booking is None:
        if changed:
            db.session.commit()
        return resolved_booking_id, changed

    if booking.status == "created":
        booking.status = "confirmed"
        changed = True
        db.session.add(
            BookingStatusHistoryDB(
                booking_id=booking.id,
                from_status="created",
                to_status="confirmed",
                source="payment_success",
            )
        )

    if changed:
        db.session.commit()

    return resolved_booking_id, changed


def fail_payment_and_cleanup_created_booking(
    *,
    payment_id: int | None = None,
    booking_id: int | None = None,
    reason: str,
) -> tuple[int | None, bool]:
    """Mark payment failed and delete booking aggregate when still in created state.

    Returns (resolved_booking_id, deleted).
    """
    _ = reason
    resolved_booking_id = _resolve_booking_id(payment_id, booking_id)
    if resolved_booking_id is None:
        return None, False

    payment = db.session.get(PaymentDB, payment_id) if payment_id is not None else None
    if payment is not None and payment.status not in {"paid", "failed"}:
        payment.status = "failed"

    booking = db.session.get(BookingDB, resolved_booking_id)
    if booking is None:
        db.session.commit()
        return resolved_booking_id, False

    # Never delete successful bookings.
    if payment is not None and payment.status == "paid":
        db.session.commit()
        return resolved_booking_id, False

    if booking.status != "created":
        db.session.commit()
        return resolved_booking_id, False

    db.session.query(ReservationQRCodeDB).filter(
        ReservationQRCodeDB.reservation_id == resolved_booking_id
    ).delete(synchronize_session=False)
    db.session.query(GameReservationDB).filter(
        GameReservationDB.booking_id == resolved_booking_id
    ).delete(synchronize_session=False)
    db.session.query(TableReservationDB).filter(
        TableReservationDB.booking_id == resolved_booking_id
    ).delete(synchronize_session=False)
    db.session.query(PaymentDB).filter(
        PaymentDB.booking_id == resolved_booking_id
    ).delete(synchronize_session=False)
    db.session.query(BookingStatusHistoryDB).filter(
        BookingStatusHistoryDB.booking_id == resolved_booking_id
    ).delete(synchronize_session=False)
    db.session.query(BookingDB).filter(BookingDB.id == resolved_booking_id).delete(
        synchronize_session=False
    )
    db.session.commit()

    return resolved_booking_id, True
