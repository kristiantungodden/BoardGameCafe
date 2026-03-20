"""Reservation domain events."""

from datetime import datetime
from typing import Optional
from .domain_event import DomainEvent


class ReservationRequested(DomainEvent):
    """Raised when a reservation is requested."""
    
    customer_id: int
    table_id: int
    party_size: int
    reserved_at: datetime
    reserved_until: datetime


class ReservationConfirmed(DomainEvent):
    """Raised when a reservation is confirmed."""
    
    customer_id: int
    table_id: int


class ReservationCancelled(DomainEvent):
    """Raised when a reservation is cancelled."""
    
    reason: Optional[str] = None


class ReservationNoShow(DomainEvent):
    """Raised when customer doesn't show up."""
    
    pass


class ReservationSeated(DomainEvent):
    """Raised when party is seated."""
    
    table_id: int
    seated_at: datetime


class ReservationCompleted(DomainEvent):
    """Raised when reservation session is completed."""
    
    completed_at: datetime
