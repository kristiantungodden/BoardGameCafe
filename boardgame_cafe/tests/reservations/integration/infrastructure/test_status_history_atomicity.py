from datetime import datetime, timedelta

import pytest

from features.bookings.application.use_cases.booking_lifecycle_use_cases import CancelBookingUseCase
from features.bookings.domain.models.booking import Booking
from features.reservations.infrastructure.repositories.reservation_repository import (
    SqlAlchemyReservationRepository,
)
from features.tables.infrastructure.database.table_db import TableDB
from shared.infrastructure import db


class FailingStatusHistoryRepository:
    def __init__(self, session=None, auto_commit=True):
        self.session = session
        self.auto_commit = auto_commit

    def save(self, entry):
        raise RuntimeError("history write failed")


@pytest.mark.integration
def test_cancel_transition_rolls_back_when_history_write_fails(app):
    with app.app_context():
        table = TableDB(table_nr="501", capacity=4, floor=1, zone="A", status="available")
        db.session.add(table)
        db.session.commit()

        repo = SqlAlchemyReservationRepository()
        booking = Booking(
            customer_id=11,
            start_ts=datetime.now() + timedelta(days=1),
            end_ts=datetime.now() + timedelta(days=1, hours=2),
            party_size=2,
            status="confirmed",
        )
        setattr(booking, "table_id", table.id)
        booking = repo.add(booking)

        use_case = CancelBookingUseCase(
            booking_repo=repo,
            status_history_repo=FailingStatusHistoryRepository(),
        )

        with pytest.raises(RuntimeError, match="history write failed"):
            use_case.execute(booking.id)

        unchanged = repo.get_by_id(booking.id)
        assert unchanged is not None
        assert unchanged.status == "confirmed"
