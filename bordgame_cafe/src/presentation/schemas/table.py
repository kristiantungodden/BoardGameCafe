"""Table schema."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TableBase(BaseModel):
    """Base table schema."""
    number: int
    capacity: int
    location: str
    features: Optional[List[str]] = None


class TableCreate(TableBase):
    """Schema for creating a table."""
    pass


class TableUpdate(BaseModel):
    """Schema for updating a table."""
    number: Optional[int] = None
    capacity: Optional[int] = None
    location: Optional[str] = None
    features: Optional[List[str]] = None


class TableResponse(TableBase):
    """Schema for table response."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
