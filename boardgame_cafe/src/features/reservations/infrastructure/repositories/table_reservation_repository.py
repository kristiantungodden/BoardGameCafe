"""SQLAlchemy implementation of TableReservationRepository."""
from typing import Optional, Sequence

from features.bookings.infrastructure.database.booking_db import BookingDB
from shared.infrastructure import db
from features.reservations.domain.models.table_reservation import TableReservation
from features.reservations.application.interfaces.table_reservation_repository_interface import (
    TableReservationRepositoryInterface,
)
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB


class SqlAlchemyTableReservationRepository(TableReservationRepositoryInterface):
    """SQLAlchemy implementation of TableReservationRepository."""
    
    def __init__(self, session=None, auto_commit: bool = True):
        self.session = session or db.session
        self.auto_commit = auto_commit
    
    def save(self, table_reservation: TableReservation) -> TableReservation:
        """Save a new table reservation link."""
        booking = self.session.get(BookingDB, table_reservation.booking_id)
        if booking is None:
            raise ValueError(f"Booking with id {table_reservation.booking_id} not found")

        db_table_res = TableReservationDB(
            customer_id=booking.customer_id,
            start_ts=booking.start_ts,
            end_ts=booking.end_ts,
            party_size=booking.party_size,
            status=booking.status,
            notes=booking.notes,
            created_at=booking.created_at,
            booking_id=table_reservation.booking_id,
            table_id=table_reservation.table_id,
        )
        self.session.add(db_table_res)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        
        table_reservation.id = db_table_res.id
        return table_reservation
    
    def get_by_id(self, table_reservation_link_id: int) -> Optional[TableReservation]:
        """Get a table reservation by id."""
        db_table_res = (
            self.session.query(TableReservationDB)
            .filter_by(id=table_reservation_link_id)
            .first()
        )
        if db_table_res is None:
            return None
        
        return self._to_domain(db_table_res)
    
    def delete(self, table_reservation_link_id: int) -> None:
        """Delete a table reservation by id."""
        db_table_res = (
            self.session.query(TableReservationDB)
            .filter_by(id=table_reservation_link_id)
            .first()
        )
        if db_table_res is not None:
            self.session.delete(db_table_res)
            if self.auto_commit:
                self.session.commit()
            else:
                self.session.flush()
    
    def list_by_booking_id(self, booking_id: int) -> Sequence[TableReservation]:
        """List all table reservations for a booking."""
        db_table_ress = (
            self.session.query(TableReservationDB)
            .filter_by(booking_id=booking_id)
            .all()
        )
        return [self._to_domain(db) for db in db_table_ress]

    def list_by_table_id(self, table_id: int) -> Sequence[TableReservation]:
        """List all table reservations linked to a table."""
        db_table_ress = (
            self.session.query(TableReservationDB)
            .filter_by(table_id=table_id)
            .all()
        )
        return [self._to_domain(db) for db in db_table_ress]
    
    def get_by_booking_and_table(
        self, booking_id: int, table_id: int
    ) -> Optional[TableReservation]:
        """Get a table reservation by booking_id and table_id."""
        db_table_res = (
            self.session.query(TableReservationDB)
            .filter_by(booking_id=booking_id, table_id=table_id)
            .first()
        )
        if db_table_res is None:
            return None
        
        return self._to_domain(db_table_res)
    
    @staticmethod
    def _to_domain(db_table_res: TableReservationDB) -> TableReservation:
        """Convert database model to domain model."""
        return TableReservation(
            id=db_table_res.id,
            booking_id=db_table_res.booking_id,
            table_id=db_table_res.table_id,
        )
