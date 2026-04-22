from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from shared.domain.exceptions import InvalidStatusTransition, ValidationError


VALID_BOOKING_STATUSES = {
    "created",
    "confirmed",
    "seated",
    "completed",
    "cancelled",
    "no_show",
}


@dataclass
class Booking:
    customer_id: int
    start_ts: datetime
    end_ts: datetime
    party_size: int
    status: str = "created"
    notes: Optional[str] = None
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.customer_id <= 0:
            raise ValidationError("customer_id must be a positive integer")
        if self.party_size <= 0:
            raise ValidationError("party_size must be a positive integer")
        if self.end_ts <= self.start_ts:
            raise ValidationError("end_ts must be after start_ts")
        if self.status not in VALID_BOOKING_STATUSES:
            raise ValidationError(
                f"status must be one of: {', '.join(sorted(VALID_BOOKING_STATUSES))}"
            )

    def seat(self) -> None:
        if self.status != "confirmed":
            raise InvalidStatusTransition(
                f"Cannot seat booking in status '{self.status}'"
            )
        self.status = "seated"

    def confirm(self) -> None:
        if self.status != "created":
            raise InvalidStatusTransition(
                f"Cannot confirm booking in status '{self.status}'"
            )
        self.status = "confirmed"

    def cancel(self) -> None:
        if self.status != "confirmed":
            raise InvalidStatusTransition(
                f"Cannot cancel booking in status '{self.status}'"
            )
        self.status = "cancelled"

    def complete(self) -> None:
        if self.status != "seated":
            raise InvalidStatusTransition(
                f"Cannot complete booking in status '{self.status}'"
            )
        self.status = "completed"

    def mark_no_show(self) -> None:
        if self.status != "confirmed":
            raise InvalidStatusTransition(
                f"Cannot mark no-show for booking in status '{self.status}'"
            )
        self.status = "no_show"

    def overlaps(self, other: "Booking") -> bool:
        if self.customer_id != other.customer_id:
            return False
        return self.start_ts < other.end_ts and other.start_ts < self.end_ts
