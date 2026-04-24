from datetime import datetime, timedelta

from features.payments.application.services.booking_payment_lifecycle import (
    confirm_booking_after_success,
    fail_payment_and_cleanup_created_booking,
)
from features.bookings.infrastructure.repositories.booking_repository import (
    SqlAlchemyBookingRepository,
)
from features.bookings.infrastructure.repositories.booking_status_history_repository import (
    SqlAlchemyBookingStatusHistoryRepository,
)
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.bookings.infrastructure.database.booking_status_history_db import (
    BookingStatusHistoryDB,
)
from features.payments.domain.models.payment import Payment, PaymentStatus
from features.payments.infrastructure.repositories.payment_repository import PaymentRepository
from features.reservations.infrastructure.repositories.game_reservation_repository import (
    SqlAlchemyGameReservationRepository,
)
from features.reservations.infrastructure.repositories.reservation_qr_repository import (
    SqlAlchemyReservationQRCodeRepository,
)
from features.reservations.infrastructure.database.table_reservations_db import (
    TableReservationDB,
)
from features.reservations.infrastructure.repositories.table_reservation_repository import (
    SqlAlchemyTableReservationRepository,
)
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.database.user_db import UserDB
from shared.infrastructure import db


def _create_user(email: str) -> UserDB:
    user = UserDB(name="Customer", email=email, password_hash="hashed", role="customer")
    db.session.add(user)
    db.session.commit()
    return user


def _create_table(table_nr: str) -> TableDB:
    table = TableDB(
        table_nr=table_nr,
        capacity=4,
        floor=1,
        zone="main",
        status="available",
    )
    db.session.add(table)
    db.session.commit()
    return table


def _create_created_booking(customer_id: int, table_id: int, *, booking_id: int) -> BookingDB:
    start_ts = datetime(2026, 4, 22, 18, 0)
    booking = BookingDB(
        id=booking_id,
        customer_id=customer_id,
        start_ts=start_ts,
        end_ts=start_ts + timedelta(hours=2),
        party_size=4,
        status="created",
    )
    db.session.add(booking)
    db.session.flush()
    db.session.add(TableReservationDB(booking_id=booking.id, table_id=table_id))
    db.session.add(
        BookingStatusHistoryDB(
            booking_id=booking.id,
            from_status=None,
            to_status="created",
            source="create",
        )
    )
    db.session.commit()
    return booking


def test_confirm_booking_after_success_marks_booking_paid_and_confirmed(app):
    repo = PaymentRepository()
    booking_repo = SqlAlchemyBookingRepository()
    history_repo = SqlAlchemyBookingStatusHistoryRepository()

    with app.app_context():
        customer = _create_user("payment-success@test.local")
        table = _create_table("LC-1")
        booking = _create_created_booking(customer.id, table.id, booking_id=901)

        payment = Payment(booking_id=booking.id, amount_cents=2500)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_success"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

        resolved_booking_id, changed = confirm_booking_after_success(
            payment_repo=repo,
            booking_repo=booking_repo,
            status_history_repo=history_repo,
            payment_id=saved.id,
            booking_id=booking.id,
        )

        assert resolved_booking_id == booking.id
        assert changed is True

        updated_payment = repo.get_by_id(saved.id)
        updated_booking = db.session.get(BookingDB, booking.id)
        history_rows = db.session.query(BookingStatusHistoryDB).filter_by(
            booking_id=booking.id
        ).all()

        assert updated_payment is not None
        assert updated_payment.status == PaymentStatus.PAID
        assert updated_booking is not None
        assert updated_booking.status == "confirmed"
        assert len(history_rows) == 2
        assert history_rows[-1].from_status == "created"
        assert history_rows[-1].to_status == "confirmed"
        assert history_rows[-1].source == "payment_success"


def test_fail_payment_and_cleanup_created_booking_removes_aggregate(app):
    repo = PaymentRepository()
    booking_repo = SqlAlchemyBookingRepository()
    history_repo = SqlAlchemyBookingStatusHistoryRepository()
    table_repo = SqlAlchemyTableReservationRepository()
    game_repo = SqlAlchemyGameReservationRepository()
    qr_repo = SqlAlchemyReservationQRCodeRepository()

    with app.app_context():
        customer = _create_user("payment-failure@test.local")
        table = _create_table("LC-2")
        booking = _create_created_booking(customer.id, table.id, booking_id=902)

        payment = Payment(booking_id=booking.id, amount_cents=2500)
        saved = repo.add(payment)
        saved.provider = "stripe"
        saved.provider_ref = "cs_test_failure"
        saved.status = PaymentStatus.PENDING
        repo.update(saved)

        resolved_booking_id, deleted = fail_payment_and_cleanup_created_booking(
            payment_repo=repo,
            booking_repo=booking_repo,
            status_history_repo=history_repo,
            table_reservation_repo=table_repo,
            game_reservation_repo=game_repo,
            reservation_qr_repo=qr_repo,
            payment_id=saved.id,
            booking_id=booking.id,
            reason="customer_cancelled",
        )

        assert resolved_booking_id == booking.id
        assert deleted is True
        assert repo.get_by_id(saved.id) is None
        assert db.session.get(BookingDB, booking.id) is None
        assert db.session.query(TableReservationDB).filter_by(booking_id=booking.id).count() == 0
        assert db.session.query(BookingStatusHistoryDB).filter_by(booking_id=booking.id).count() == 0