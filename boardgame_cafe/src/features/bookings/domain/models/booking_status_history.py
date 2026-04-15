from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from features.bookings.domain.models.booking import VALID_BOOKING_STATUSES
from shared.domain.exceptions import ValidationError


@dataclass
class BookingStatusHistoryEntry:
    booking_id: int
    to_status: str
    from_status: Optional[str] = None
    source: Optional[str] = None
    reason: Optional[str] = None
    actor_user_id: Optional[int] = None
    actor_role: Optional[str] = None
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.booking_id <= 0:
            raise ValidationError("booking_id must be a positive integer")
        if self.to_status not in VALID_BOOKING_STATUSES:
            raise ValidationError(f"Invalid to_status '{self.to_status}'")
        if (
            self.from_status is not None
            and self.from_status not in VALID_BOOKING_STATUSES
        ):
            raise ValidationError(f"Invalid from_status '{self.from_status}'")
        if self.actor_user_id is not None and self.actor_user_id <= 0:
            raise ValidationError("actor_user_id must be a positive integer")
