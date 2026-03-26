from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Query, Session

from application.interfaces.repositories.table_repository import TableFilters, TableRepository as TableRepositoryInterface
from domain.models.table import Table
from infrastructure import db
from infrastructure.database import CafeTable as CafeTableDB

class TableRepository(TableRepositoryInterface):
    def __init__(self, session: Optional[Session] = None):
        self.session = session or db.session

    def add(self, table: Table) -> Table:
        db_table = CafeTableDB(
            table_nr=str(table.number),
            capacity=table.capacity,
            zone=table.zone,
            features=table.features or {},
            status=table.status,
        )
        self.session.add(db_table)
        self.session.commit()
        return self._to_domain(db_table)

    def get_by_id(self, table_id: int) -> Optional[Table]:
        db_table = self.session.get(CafeTableDB, table_id)
        if db_table is None:
            return None
        return self._to_domain(db_table)

    def list(self) -> list[Table]:
        db_tables = self.session.query(CafeTableDB).all()
        return [self._to_domain(item) for item in db_tables]

    def get_all(self) -> list[Table]:
        """Backward-compatible alias kept while callers migrate to list()."""
        return self.list()

    def update(self, table: Table) -> Table:
        table_id = getattr(table, "id", None)
        if table_id is None:
            raise ValueError("Cannot update table without an id")

        db_table = self.session.get(CafeTableDB, table_id)
        if db_table is None:
            raise ValueError(f"Table with id {table_id} does not exist")

        db_table.table_nr = str(table.number)
        db_table.capacity = table.capacity
        db_table.zone = table.zone
        db_table.features = table.features or {}
        db_table.status = table.status
        self.session.commit()
        return self._to_domain(db_table)

    def delete(self, table_id: int) -> None:
        db_table = self.session.get(CafeTableDB, table_id)
        if db_table is None:
            raise ValueError(f"Table with id {table_id} does not exist")
        self.session.delete(db_table)
        self.session.commit()

    def search(self, filters: Optional[TableFilters] = None) -> list[Table]:
        filters = filters or TableFilters()
        query: Query = self.session.query(CafeTableDB)

        if filters.zone is not None:
            query = query.filter(CafeTableDB.zone == filters.zone)

        if filters.status is not None:
            query = query.filter(CafeTableDB.status == filters.status)

        if filters.is_available is not None:
            if filters.is_available:
                query = query.filter(CafeTableDB.status == "available")
            else:
                query = query.filter(CafeTableDB.status != "available")

        if filters.min_capacity is not None:
            query = query.filter(CafeTableDB.capacity >= filters.min_capacity)

        if filters.max_capacity is not None:
            query = query.filter(CafeTableDB.capacity <= filters.max_capacity)

        if filters.feature is not None:
            query = query.filter(CafeTableDB.features[filters.feature].as_boolean() == True)

        return [self._to_domain(item) for item in query.all()]

    def count_by_status(self) -> dict[str, int]:
        """Count tables by status. Returns all known statuses even if count is 0."""
        # Query only returns statuses that have tables
        status_counts = (
            self.session.query(CafeTableDB.status, db.func.count(CafeTableDB.id))
            .group_by(CafeTableDB.status)
            .all()
        )
        
        # Initialize all valid statuses with 0
        all_statuses = {"available", "occupied", "reserved", "maintenance"}
        result = {status: 0 for status in all_statuses}
        
        # Update with actual counts from query
        for status, count in status_counts:
            result[status] = count
        
        return result

    @staticmethod
    def _to_domain(db_table: CafeTableDB) -> Table:
        table = Table(
            number=int(db_table.table_nr),
            capacity=db_table.capacity,
            zone=db_table.zone,
            features=db_table.features or {},
            status=db_table.status,
        )
        # Domain model currently does not declare persistence metadata fields.
        table.id = db_table.id
        table.created_at = getattr(db_table, "created_at", None)
        return table
    