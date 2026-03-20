"""Base domain event."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DomainEvent(BaseModel):
    """Base class for all domain events."""
    
    event_id: Optional[str] = None
    aggregate_id: int
    timestamp: datetime = datetime.utcnow()
    
    class Config:
        use_enum_values = True
