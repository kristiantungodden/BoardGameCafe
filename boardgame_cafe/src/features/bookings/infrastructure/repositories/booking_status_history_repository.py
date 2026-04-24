from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy.orm import Session

from features.bookings.application.interfaces.booking_status_history_repository_interface import (
    BookingStatusHistoryRepositoryInterface,
)
from features.bookings.domain.models.booking_status_history import (
    BookingStatusHistoryEntry,
)
from features.bookings.infrastructure.database.booking_status_history_db import (
    BookingStatusHistoryDB,
)
from shared.infrastructure import db


class SqlAlchemyBookingStatusHistoryRepository(BookingStatusHistoryRepositoryInterface):
    def __init__(self, session: Optional[Session] = None, auto_commit: bool = True):
        self.session = session or db.session
        self.auto_commit = auto_commit

    def save(self, entry: BookingStatusHistoryEntry) -> BookingStatusHistoryEntry:
        row = BookingStatusHistoryDB(
            booking_id=entry.booking_id,
            from_status=entry.from_status,
            to_status=entry.to_status,
            source=entry.source,
            reason=entry.reason,
            actor_user_id=entry.actor_user_id,
            actor_role=entry.actor_role,
            created_at=entry.created_at,
        )
        self.session.add(row)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()

        entry.id = row.id
        if row.created_at is not None:
            entry.created_at = row.created_at
        return entry

    def list_for_booking(self, booking_id: int) -> Sequence[BookingStatusHistoryEntry]:
        rows = (
            self.session.query(BookingStatusHistoryDB)
            .filter(BookingStatusHistoryDB.booking_id == booking_id)
            .order_by(BookingStatusHistoryDB.created_at.asc(), BookingStatusHistoryDB.id.asc())
            .all()
        )
        return [self._to_domain(row) for row in rows]

    def delete_for_booking(self, booking_id: int) -> None:
        self.session.query(BookingStatusHistoryDB).filter(
            BookingStatusHistoryDB.booking_id == booking_id
        ).delete(synchronize_session=False)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()

    @staticmethod
    def _to_domain(row: BookingStatusHistoryDB) -> BookingStatusHistoryEntry:
        return BookingStatusHistoryEntry(
            id=row.id,
            booking_id=row.booking_id,
            from_status=row.from_status,
            to_status=row.to_status,
            source=row.source,
            reason=row.reason,
            actor_user_id=row.actor_user_id,
            actor_role=row.actor_role,
            created_at=row.created_at,
        )
