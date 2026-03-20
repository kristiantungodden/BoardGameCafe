"""Reservation schema."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class ReservationBase(BaseModel):
    """Base reservation schema."""
    customer_id: int
    table_id: int
    party_size: int
    reserved_at: datetime
    reserved_until: datetime
    status: str = "submitted"
    special_requests: Optional[str] = None


class ReservationCreate(BaseModel):
    """Schema for creating a reservation."""
    table_id: int
    party_size: int
    reserved_at: datetime
    reserved_until: datetime
    special_requests: Optional[str] = None


class ReservationUpdate(BaseModel):
    """Schema for updating a reservation."""
    party_size: Optional[int] = None
    reserved_at: Optional[datetime] = None
    reserved_until: Optional[datetime] = None
    status: Optional[str] = None
    special_requests: Optional[str] = None


class ReservationResponse(ReservationBase):
    """Schema for reservation response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
