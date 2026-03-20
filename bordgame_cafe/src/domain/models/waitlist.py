"""Waitlist domain model."""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WaitlistStatus(str, Enum):
    """Status of a waitlist entry."""
    
    WAITING = "waiting"
    NOTIFIED = "notified"
    EXPIRED = "expired"


class WaitlistEntry(BaseModel):
    """Waitlist entry entity for fully booked time slots."""
    
    id: Optional[int] = None
    customer_id: int
    table_id: int
    party_size: int
    requested_at: datetime
    requested_until: datetime
    status: WaitlistStatus = WaitlistStatus.WAITING
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        return f"Waitlist {self.id} - Customer {self.customer_id} - {self.party_size} people"
