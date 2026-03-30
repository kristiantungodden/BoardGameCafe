from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional, Sequence
from sqlalchemy.orm import Session

from features.reservations.application.interfaces.reservation_repository_interface import ReservationRepositoryInterface
from features.reservations.domain.models.reservation import TableReservation
from features.reservations.infrastructure.database.table_reservations_db import TableReservationDB
from shared.infrastructure import db


class SqlAlchemyReservationRepository(ReservationRepositoryInterface):
	"""Database-backed repository for table reservations."""

	def __init__(self, session: Optional[Session] = None) -> None:
		self.session = session or db.session

	def add(self, reservation: TableReservation) -> TableReservation:
		row = TableReservationDB(
			customer_id=reservation.customer_id,
			table_id=reservation.table_id,
			start_ts=reservation.start_ts,
			end_ts=reservation.end_ts,
			party_size=reservation.party_size,
			status=reservation.status,
			notes=reservation.notes,
		)
		self.session.add(row)
		self.session.commit()
		return self._to_domain(row)

	def get_by_id(self, reservation_id: int) -> Optional[TableReservation]:
		row = self.session.get(TableReservationDB, reservation_id)
		if row is None:
			return None
		return self._to_domain(row)

	def list_all(self) -> Sequence[TableReservation]:
		rows = (
			self.session.query(TableReservationDB)
			.order_by(TableReservationDB.start_ts.asc(), TableReservationDB.id.asc())
			.all()
		)
		return [self._to_domain(row) for row in rows]

	def list_for_table_in_window(
		self, table_id: int, start_ts: datetime, end_ts: datetime
	) -> Sequence[TableReservation]:
		rows = (
			self.session.query(TableReservationDB)
			.filter(TableReservationDB.table_id == table_id)
			.filter(TableReservationDB.start_ts < end_ts)
			.filter(start_ts < TableReservationDB.end_ts)
			.order_by(TableReservationDB.start_ts.asc())
			.all()
		)
		return [self._to_domain(row) for row in rows]

	def update(self, reservation: TableReservation) -> TableReservation:
		if reservation.id is None:
			raise ValueError("Cannot update reservation without an id")

		row = self.session.get(TableReservationDB, reservation.id)
		if row is None:
			raise ValueError(f"Reservation with id {reservation.id} does not exist")

		row.customer_id = reservation.customer_id
		row.table_id = reservation.table_id
		row.start_ts = reservation.start_ts
		row.end_ts = reservation.end_ts
		row.party_size = reservation.party_size
		row.status = reservation.status
		row.notes = reservation.notes

		self.session.commit()
		return self._to_domain(row)

	@staticmethod
	def _to_domain(row: TableReservationDB) -> TableReservation:
		return TableReservation(
			id=row.id,
			customer_id=row.customer_id,
			table_id=row.table_id,
			start_ts=row.start_ts,
			end_ts=row.end_ts,
			party_size=row.party_size,
			status=row.status,
			notes=row.notes,
			created_at=row.created_at,
		)


class InMemoryReservationRepository(ReservationRepositoryInterface):
	"""In-memory repository for table reservations.

	Useful for early development and tests before a database-backed
	implementation is added.
	"""

	def __init__(self) -> None:
		self._items: Dict[int, TableReservation] = {}
		self._next_id = 1

	def add(self, reservation: TableReservation) -> TableReservation:
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

	def get_by_id(self, reservation_id: int) -> Optional[TableReservation]:
		entity = self._items.get(reservation_id)
		if entity is None:
			return None
		return self._copy_reservation(entity)

	def list_all(self) -> Sequence[TableReservation]:
		items = [self._copy_reservation(entity) for entity in self._items.values()]
		items.sort(key=lambda r: (r.start_ts, r.id or 0))
		return items

	def list_for_table_in_window(
		self, table_id: int, start_ts: datetime, end_ts: datetime
	) -> Sequence[TableReservation]:
		matching = []
		for entity in self._items.values():
			if entity.table_id != table_id:
				continue

			# Overlap check for [start_ts, end_ts) style time windows.
			if entity.start_ts < end_ts and start_ts < entity.end_ts:
				matching.append(self._copy_reservation(entity))

		matching.sort(key=lambda r: r.start_ts)
		return matching

	def update(self, reservation: TableReservation) -> TableReservation:
		if reservation.id is None:
			raise ValueError("Cannot update reservation without an id")
		if reservation.id not in self._items:
			raise KeyError(f"Reservation with id {reservation.id} was not found")

		entity = self._copy_reservation(reservation)
		self._items[entity.id] = entity
		return self._copy_reservation(entity)

	@staticmethod
	def _copy_reservation(reservation: TableReservation) -> TableReservation:
		"""Create a detached domain entity copy.

		Returning copies prevents callers from mutating internal repository state
		accidentally.
		"""

		return TableReservation(
			id=reservation.id,
			customer_id=reservation.customer_id,
			table_id=reservation.table_id,
			start_ts=reservation.start_ts,
			end_ts=reservation.end_ts,
			party_size=reservation.party_size,
			status=reservation.status,
			notes=reservation.notes,
			created_at=reservation.created_at,
		)
