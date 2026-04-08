from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from shared.domain.exceptions import InvalidStatusTransition, ValidationError


VALID_RESERVATION_STATUSES = {
	"confirmed",
	"seated",
	"completed",
	"cancelled",
	"no_show",
}


@dataclass
class TableReservation:
	"""Domain entity for the `table_reservations` schema.

	This model contains business rules only. Persistence (SQLAlchemy) belongs
	in infrastructure/database/models.py.
	"""

	customer_id: int
	table_id: int
	start_ts: datetime
	end_ts: datetime
	party_size: int
	status: str = "confirmed"
	notes: Optional[str] = None
	id: Optional[int] = None
	created_at: datetime = field(default_factory=datetime.utcnow)

	def __post_init__(self) -> None:
		self._validate()

	def _validate(self) -> None:
		if self.customer_id <= 0:
			raise ValidationError("customer_id must be a positive integer")
		if self.table_id <= 0:
			raise ValidationError("table_id must be a positive integer")
		if self.party_size <= 0:
			raise ValidationError("party_size must be a positive integer")
		if self.end_ts <= self.start_ts:
			raise ValidationError("end_ts must be after start_ts")
		if self.status not in VALID_RESERVATION_STATUSES:
			raise ValidationError(
				f"status must be one of: {', '.join(sorted(VALID_RESERVATION_STATUSES))}"
			)

	def seat(self) -> None:
		"""Mark reservation as seated.

		Allowed from: confirmed.
		"""
		if self.status != "confirmed":
			raise InvalidStatusTransition(
				f"Cannot seat reservation in status '{self.status}'"
			)
		self.status = "seated"

	def cancel(self) -> None:
		"""Cancel reservation.

		Allowed from: confirmed.
		"""
		if self.status != "confirmed":
			raise InvalidStatusTransition(
				f"Cannot cancel reservation in status '{self.status}'"
			)
		self.status = "cancelled"

	def complete(self) -> None:
		"""Mark reservation as completed.

		Allowed from: seated.
		"""
		if self.status != "seated":
			raise InvalidStatusTransition(
				f"Cannot complete reservation in status '{self.status}'"
			)
		self.status = "completed"

	def mark_no_show(self) -> None:
		"""Mark reservation as no-show.

		Allowed from: confirmed.
		"""
		if self.status != "confirmed":
			raise InvalidStatusTransition(
				f"Cannot mark no-show for reservation in status '{self.status}'"
			)
		self.status = "no_show"

	def overlaps(self, other: "TableReservation") -> bool:
		"""Return True if two reservations overlap in time for same table."""
		if self.table_id != other.table_id:
			return False
		return self.start_ts < other.end_ts and other.start_ts < self.end_ts
