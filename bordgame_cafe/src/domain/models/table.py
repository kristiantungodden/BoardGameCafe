"""Table domain model."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Table(BaseModel):
    """Table entity."""
    
    id: Optional[int] = None
    number: int
    capacity: int
    location: str  # zone or location description
    features: Optional[list[str]] = None  # e.g., ["outdoor", "power_outlet"]
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        return f"Table {self.number} (capacity: {self.capacity})"
