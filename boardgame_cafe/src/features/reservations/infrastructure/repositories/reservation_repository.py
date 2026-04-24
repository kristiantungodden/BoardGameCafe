from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Sequence

from sqlalchemy.orm import Session

from features.bookings.domain.models.booking import Booking
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.reservations.application.interfaces.reservation_repository_interface import (
    ReservationRepositoryInterface,
)
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from shared.infrastructure import db


class SqlAlchemyReservationRepository(ReservationRepositoryInterface):
    """Compatibility repository exposing reservation-shaped views backed by booking tables."""

    def __init__(self, session: Optional[Session] = None, auto_commit: bool = True) -> None:
        self.session = session or db.session
        self.auto_commit = auto_commit

    def add(self, reservation: Booking) -> Booking:
        table_id = getattr(reservation, "table_id", None)
        if table_id is None:
            raise ValueError("Reservation requires table_id metadata")

        booking = BookingDB(
            customer_id=reservation.customer_id,
            start_ts=reservation.start_ts,
            end_ts=reservation.end_ts,
            party_size=reservation.party_size,
            status=reservation.status,
            notes=reservation.notes,
            created_at=reservation.created_at,
        )
        self.session.add(booking)
        self.session.flush()

        link = TableReservationDB(booking_id=booking.id, table_id=table_id)
        self.session.add(link)

        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()

        return self._to_domain(booking, [link.table_id])

    def get_by_id(self, reservation_id: int) -> Optional[Booking]:
        booking = self.session.get(BookingDB, reservation_id)
        if booking is None:
            return None

        table_ids = self._table_ids_for_booking(booking.id)
        if not table_ids:
            return None

        return self._to_domain(booking, table_ids)

    def list_all(self) -> Sequence[Booking]:
        rows = (
            self.session.query(BookingDB)
            .join(TableReservationDB, TableReservationDB.booking_id == BookingDB.id)
            .order_by(BookingDB.start_ts.asc(), BookingDB.id.asc())
            .all()
        )
        deduped: list[Booking] = []
        seen_booking_ids: set[int] = set()
        for booking in rows:
            if booking.id in seen_booking_ids:
                continue
            seen_booking_ids.add(booking.id)
            table_ids = self._table_ids_for_booking(booking.id)
            if not table_ids:
                continue
            deduped.append(self._to_domain(booking, table_ids))
        return deduped

    def list_for_table_in_window(
        self, table_id: int, start_ts: datetime, end_ts: datetime
    ) -> Sequence[Booking]:
        rows = (
            self.session.query(BookingDB)
            .join(TableReservationDB, TableReservationDB.booking_id == BookingDB.id)
            .filter(TableReservationDB.table_id == table_id)
            .filter(BookingDB.start_ts < end_ts)
            .filter(start_ts < BookingDB.end_ts)
            .order_by(BookingDB.start_ts.asc())
            .all()
        )
        return [self._to_domain(booking, self._table_ids_for_booking(booking.id)) for booking in rows]

    def update(self, reservation: Booking) -> Booking:
        if reservation.id is None:
            raise ValueError("Cannot update reservation without an id")

        booking = self.session.get(BookingDB, reservation.id)
        if booking is None:
            raise ValueError(f"Reservation with id {reservation.id} does not exist")

        link = (
            self.session.query(TableReservationDB)
            .filter(TableReservationDB.booking_id == booking.id)
            .order_by(TableReservationDB.id.asc())
            .first()
        )
        if link is None:
            raise ValueError(
                f"Table reservation link for reservation id {reservation.id} does not exist"
            )

        booking.customer_id = reservation.customer_id
        booking.start_ts = reservation.start_ts
        booking.end_ts = reservation.end_ts
        booking.party_size = reservation.party_size
        booking.status = reservation.status
        booking.notes = reservation.notes
        table_id = getattr(reservation, "table_id", None)
        if table_id is None:
            raise ValueError("Reservation requires table_id metadata")
        link.table_id = table_id

        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()

        return self._to_domain(booking, self._table_ids_for_booking(booking.id))

    def _table_ids_for_booking(self, booking_id: int) -> list[int]:
        rows = (
            self.session.query(TableReservationDB.table_id)
            .filter(TableReservationDB.booking_id == booking_id)
            .order_by(TableReservationDB.id.asc())
            .all()
        )
        return [int(row.table_id) for row in rows if row.table_id is not None]

    @staticmethod
    def _to_domain(booking: BookingDB, table_ids: Sequence[int]) -> Booking:
        reservation = Booking(
            id=booking.id,
            customer_id=booking.customer_id,
            start_ts=booking.start_ts,
            end_ts=booking.end_ts,
            party_size=booking.party_size,
            status=booking.status,
            notes=booking.notes,
            created_at=booking.created_at,
        )
        normalized_table_ids = [int(table_id) for table_id in table_ids if table_id is not None]
        setattr(reservation, "table_ids", normalized_table_ids)
        setattr(reservation, "table_id", normalized_table_ids[0] if normalized_table_ids else None)
        return reservation


class InMemoryReservationRepository(ReservationRepositoryInterface):
    """In-memory repository for table reservations."""

    def __init__(self) -> None:
        self._items: Dict[int, Booking] = {}
        self._next_id = 1

    def add(self, reservation: Booking) -> Booking:
        entity = self._copy_reservation(reservation)

        if entity.id is None:
            entity.id = self._next_id
            self._next_id += 1
        elif entity.id in self._items:
            raise ValueError(f"Reservation with id {entity.id} already exists")
        elif entity.id >= self._next_id:
            self._next_id = entity.id + 1

        self._items[entity.id] = entity
        return self._copy_reservation(entity)

    def get_by_id(self, reservation_id: int) -> Optional[Booking]:
        entity = self._items.get(reservation_id)
        if entity is None:
            return None
        return self._copy_reservation(entity)

    def list_all(self) -> Sequence[Booking]:
        items = [self._copy_reservation(entity) for entity in self._items.values()]
        items.sort(key=lambda r: (r.start_ts, r.id or 0))
        return items

    def list_for_table_in_window(
        self, table_id: int, start_ts: datetime, end_ts: datetime
    ) -> Sequence[Booking]:
        matching = []
        for entity in self._items.values():
            if getattr(entity, "table_id", None) != table_id:
                continue
            if entity.start_ts < end_ts and start_ts < entity.end_ts:
                matching.append(self._copy_reservation(entity))

        matching.sort(key=lambda r: r.start_ts)
        return matching

    def update(self, reservation: Booking) -> Booking:
        if reservation.id is None:
            raise ValueError("Cannot update reservation without an id")
        if reservation.id not in self._items:
            raise KeyError(f"Reservation with id {reservation.id} was not found")

        entity = self._copy_reservation(reservation)
        self._items[entity.id] = entity
        return self._copy_reservation(entity)

    @staticmethod
    def _copy_reservation(reservation: Booking) -> Booking:
        copied = Booking(
            id=reservation.id,
            customer_id=reservation.customer_id,
            start_ts=reservation.start_ts,
            end_ts=reservation.end_ts,
            party_size=reservation.party_size,
            status=reservation.status,
            notes=reservation.notes,
            created_at=reservation.created_at,
        )
        setattr(copied, "table_id", getattr(reservation, "table_id", None))
        return copied
