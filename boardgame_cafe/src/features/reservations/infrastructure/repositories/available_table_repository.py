from datetime import datetime
from typing import Optional

from features.reservations.application.interfaces.available_table_repository_interface import (
    AvailableTableRepositoryInterface,
)
from features.bookings.infrastructure.database.booking_db import BookingDB
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from features.tables.infrastructure.database.table_db import TableDB
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES
from shared.infrastructure import db


class SqlAlchemyAvailableTableRepository(AvailableTableRepositoryInterface):
    """SQLAlchemy implementation for querying available tables."""

    def __init__(self, session=None):
        self.session = session or db.session

    def get_blocked_table_ids(self, start_ts: datetime, end_ts: datetime) -> set[int]:
        """Get table IDs blocked during the given time window."""
        rows = (
            self.session.query(TableReservationDB.table_id)
            .join(BookingDB, TableReservationDB.booking_id == BookingDB.id)
            .filter(BookingDB.status.in_(OVERLAP_BLOCKING_STATUSES))
            .filter(BookingDB.start_ts < end_ts)
            .filter(start_ts < BookingDB.end_ts)
            .all()
        )
        return {row[0] for row in rows}

    def find_best_available_table(
        self, party_size: int, start_ts: datetime, end_ts: datetime
    ) -> Optional[int]:
        """Find the smallest available table that fits party_size and is not blocked during window."""
        blocked = self.get_blocked_table_ids(start_ts, end_ts)
        query = (
            self.session.query(TableDB)
            .filter(TableDB.status == "available")
            .filter(TableDB.capacity >= party_size)
        )
        if blocked:
            query = query.filter(~TableDB.id.in_(blocked))

        candidate = query.order_by(TableDB.capacity.asc(), TableDB.id.asc()).first()
        return candidate.id if candidate else None

    def validate_table_selection(
        self, table_id: int, party_size: int, start_ts: datetime, end_ts: datetime
    ) -> bool:
        table = self.session.get(TableDB, table_id)
        if table is None:
            return False
        if table.status != "available":
            return False
        if table.capacity < party_size:
            return False

        blocked = self.get_blocked_table_ids(start_ts, end_ts)
        return table_id not in blocked
