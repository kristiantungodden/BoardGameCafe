from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
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

_SEATING_WINDOW = timedelta(minutes=15)


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

    def seat(self, current_time: Optional[datetime] = None) -> None:
        if self.status != "confirmed":
            raise InvalidStatusTransition(
                f"Cannot seat booking in status '{self.status}'"
            )

        now = current_time
        if now is None:
            now = (
                datetime.now(tz=self.start_ts.tzinfo)
                if self.start_ts.tzinfo
                else datetime.now(timezone.utc).replace(tzinfo=None)
            )

        if self.start_ts.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        elif self.start_ts.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=self.start_ts.tzinfo)

        if now < self.start_ts - _SEATING_WINDOW:
            raise ValidationError(
                "Booking can only be seated 15 minutes before start time or later"
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
