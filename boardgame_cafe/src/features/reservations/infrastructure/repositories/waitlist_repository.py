from __future__ import annotations

from typing import Sequence

from shared.infrastructure import db
from features.reservations.application.interfaces.waitlist_repository_interface import (
    WaitlistRepositoryInterface,
)
from features.reservations.domain.models.waitlist_entry import WaitlistEntry
from features.reservations.infrastructure.database.waitlist_db import WaitlistDB


class SqlAlchemyWaitlistRepository(WaitlistRepositoryInterface):
    def __init__(self, session=None, auto_commit: bool = True) -> None:
        self.session = session or db.session
        self.auto_commit = auto_commit

    def add(self, entry: WaitlistEntry) -> WaitlistEntry:
        row = WaitlistDB(
            customer_id=entry.customer_id,
            party_size=entry.party_size,
            notes=entry.notes,
        )
        self.session.add(row)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        return WaitlistEntry(id=row.id, customer_id=row.customer_id, party_size=row.party_size, notes=row.notes, created_at=row.created_at)

    def list_all(self) -> Sequence[WaitlistEntry]:
        rows = self.session.query(WaitlistDB).order_by(WaitlistDB.created_at.asc()).all()
        return [WaitlistEntry(id=r.id, customer_id=r.customer_id, party_size=r.party_size, notes=r.notes, created_at=r.created_at) for r in rows]

    def remove(self, entry_id: int) -> bool:
        row = self.session.get(WaitlistDB, entry_id)
        if row is None:
            return False
        self.session.delete(row)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        return True
