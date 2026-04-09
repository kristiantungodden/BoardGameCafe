from datetime import datetime
from typing import Optional, Sequence

from features.bookings.application.interfaces.booking_repository_interface import (
    BookingRepositoryInterface,
)
from features.bookings.domain.models.booking import Booking
from features.bookings.infrastructure.database.booking_db import BookingDB
from shared.infrastructure import db


class SqlAlchemyBookingRepository(BookingRepositoryInterface):
    def __init__(self, session=None, auto_commit: bool = True):
        self.session = session or db.session
        self.auto_commit = auto_commit

    def save(self, booking: Booking) -> Booking:
        db_booking = BookingDB(
            customer_id=booking.customer_id,
            start_ts=booking.start_ts,
            end_ts=booking.end_ts,
            party_size=booking.party_size,
            status=booking.status,
            notes=booking.notes,
            created_at=booking.created_at,
        )
        self.session.add(db_booking)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()

        booking.id = db_booking.id
        return booking

    def update(self, booking: Booking) -> Booking:
        db_booking = self.session.query(BookingDB).filter_by(id=booking.id).first()
        if db_booking is None:
            raise ValueError(f"Booking with id {booking.id} not found")

        db_booking.customer_id = booking.customer_id
        db_booking.start_ts = booking.start_ts
        db_booking.end_ts = booking.end_ts
        db_booking.party_size = booking.party_size
        db_booking.status = booking.status
        db_booking.notes = booking.notes

        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()

        return booking

    def get_by_id(self, booking_id: int) -> Optional[Booking]:
        db_booking = self.session.query(BookingDB).filter_by(id=booking_id).first()
        if db_booking is None:
            return None

        return self._to_domain(db_booking)

    def delete(self, booking_id: int) -> None:
        db_booking = self.session.query(BookingDB).filter_by(id=booking_id).first()
        if db_booking is not None:
            self.session.delete(db_booking)
            if self.auto_commit:
                self.session.commit()
            else:
                self.session.flush()

    def list_by_customer(self, customer_id: int) -> Sequence[Booking]:
        db_bookings = (
            self.session.query(BookingDB)
            .filter_by(customer_id=customer_id)
            .order_by(BookingDB.start_ts.asc(), BookingDB.id.asc())
            .all()
        )
        return [self._to_domain(db_booking) for db_booking in db_bookings]

    def list_all(self) -> Sequence[Booking]:
        db_bookings = (
            self.session.query(BookingDB)
            .order_by(BookingDB.start_ts.asc(), BookingDB.id.asc())
            .all()
        )
        return [self._to_domain(db_booking) for db_booking in db_bookings]

    def find_overlapping_bookings(
        self,
        customer_id: int,
        start_ts: datetime,
        end_ts: datetime,
        statuses: set[str],
    ) -> Sequence[Booking]:
        db_bookings = (
            self.session.query(BookingDB)
            .filter(
                BookingDB.customer_id == customer_id,
                BookingDB.start_ts < end_ts,
                BookingDB.end_ts > start_ts,
                BookingDB.status.in_(statuses),
            )
            .all()
        )
        return [self._to_domain(db_booking) for db_booking in db_bookings]

    @staticmethod
    def _to_domain(db_booking: BookingDB) -> Booking:
        return Booking(
            id=db_booking.id,
            customer_id=db_booking.customer_id,
            start_ts=db_booking.start_ts,
            end_ts=db_booking.end_ts,
            party_size=db_booking.party_size,
            status=db_booking.status,
            notes=db_booking.notes,
            created_at=db_booking.created_at,
        )
