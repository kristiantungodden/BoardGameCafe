from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shared.domain.exceptions import InvalidStatusTransition, ValidationError
VALID_TABLE_STATUSES = {"available", "occupied", "reserved", "maintenance"}

@dataclass
class Table:
    """Domain entity for the `tables` schema.

    This model contains business rules only. Persistence (SQLAlchemy) belongs
    in infrastructure/database/models.py.
    """

    number: int
    capacity: int
    zone: Optional[str] = None
    features: Optional[dict[str, bool]] = None
    status: str = "available"

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.number <= 0 or self.number != int(self.number):
            raise ValidationError("number must be a positive integer")
        if self.capacity <= 0 or self.capacity != int(self.capacity):
            raise ValidationError("capacity must be a positive integer")
        if self.status not in VALID_TABLE_STATUSES:
            raise ValidationError(
                f"status must be one of: {', '.join(sorted(VALID_TABLE_STATUSES))}"
            )

    def occupy(self) -> None:
        """Mark table as occupied.

        Allowed from: available, reserved.
        """
        if self.status not in {"available", "reserved"}:
            raise InvalidStatusTransition(
                f"Cannot occupy table in status '{self.status}'"
            )
        self.status = "occupied"

    def free(self) -> None:
        """Mark table as available.

        Allowed from: occupied, reserved.
        """
        if self.status not in {"occupied", "reserved"}:
            raise InvalidStatusTransition(
                f"Cannot free table in status '{self.status}'"
            )
        self.status = "available"

    def reserve(self) -> None:
        """Mark table as reserved.

        Allowed from: available.
        """
        if self.status != "available":
            raise InvalidStatusTransition(
                f"Cannot reserve table in status '{self.status}'"
            )
        self.status = "reserved"

    def start_maintenance(self) -> None:
        """Mark table as under maintenance.

        Allowed from: available.
        """
        if self.status != "available":
            raise InvalidStatusTransition(
                f"Cannot start maintenance for table in status '{self.status}'"
            )
        self.status = "maintenance"
    
    def finish_maintenance(self) -> None:
        """Mark table as available after maintenance.

        Allowed from: maintenance.
        """
        if self.status != "maintenance":
            raise InvalidStatusTransition(
                f"Cannot finish maintenance for table in status '{self.status}'"
            )
        self.status = "available"