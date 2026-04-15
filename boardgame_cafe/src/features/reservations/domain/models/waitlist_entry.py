from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class WaitlistEntry:
    id: Optional[int]
    customer_id: int
    party_size: int
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "party_size": self.party_size,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }
