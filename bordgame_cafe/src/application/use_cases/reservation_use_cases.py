"""Reservation-related use cases."""

from datetime import datetime
from pydantic import BaseModel
from domain.models import Reservation, ReservationStatus
from domain.exceptions import (
    ReservationNotFound,
    PartyTooLarge,
    OverlappingReservation,
    TableNotFound,
)


class CreateReservationRequest(BaseModel):
    """Request for creating a new reservation."""
    
    customer_id: int
    table_id: int
    party_size: int
    reserved_at: datetime
    reserved_until: datetime
    special_requests: str = ""


class CreateReservationUseCase:
    """Use case for creating a reservation."""
    
    def __init__(self, reservation_repository, table_repository) -> None:
        self.reservation_repository = reservation_repository
        self.table_repository = table_repository
    
    async def execute(self, request: CreateReservationRequest) -> Reservation:
        """
        Create a new reservation.
        
        Args:
            request: Reservation details
            
        Returns:
            Created reservation
            
        Raises:
            TableNotFound: If table doesn't exist
            PartyTooLarge: If party size exceeds table capacity
            OverlappingReservation: If time slot is already reserved
        """
        # Get table
        table = await self.table_repository.get_by_id(request.table_id)
        if not table:
            raise TableNotFound(f"Table {request.table_id} not found")
        
        # Check party size
        if request.party_size > table.capacity:
            raise PartyTooLarge(
                f"Party size {request.party_size} exceeds table capacity {table.capacity}"
            )
        
        # Check for overlapping reservations
        overlapping = await self.reservation_repository.get_overlapping(
            request.table_id,
            request.reserved_at,
            request.reserved_until,
        )
        if overlapping:
            raise OverlappingReservation(
                f"Table {request.table_id} is already reserved for this time slot"
            )
        
        # Create reservation
        reservation = Reservation(
            customer_id=request.customer_id,
            table_id=request.table_id,
            party_size=request.party_size,
            reserved_at=request.reserved_at,
            reserved_until=request.reserved_until,
            status=ReservationStatus.SUBMITTED,
            special_requests=request.special_requests,
        )
        
        await self.reservation_repository.add(reservation)
        return reservation


class CancelReservationRequest(BaseModel):
    """Request for cancelling a reservation."""
    
    reservation_id: int
    reason: str = ""


class CancelReservationUseCase:
    """Use case for cancelling a reservation."""
    
    def __init__(self, reservation_repository) -> None:
        self.reservation_repository = reservation_repository
    
    async def execute(self, request: CancelReservationRequest) -> Reservation:
        """
        Cancel a reservation.
        
        Args:
            request: Cancellation request
            
        Returns:
            Updated reservation
            
        Raises:
            ReservationNotFound: If reservation doesn't exist
        """
        reservation = await self.reservation_repository.get_by_id(request.reservation_id)
        if not reservation:
            raise ReservationNotFound(f"Reservation {request.reservation_id} not found")
        
        reservation.status = ReservationStatus.CANCELLED
        await self.reservation_repository.update(reservation)
        return reservation


class ConfirmReservationRequest(BaseModel):
    """Request for confirming a reservation."""
    
    reservation_id: int


class ConfirmReservationUseCase:
    """Use case for confirming a reservation."""
    
    def __init__(self, reservation_repository) -> None:
        self.reservation_repository = reservation_repository
    
    async def execute(self, request: ConfirmReservationRequest) -> Reservation:
        """
        Confirm a reservation.
        
        Args:
            request: Confirmation request
            
        Returns:
            Updated reservation
            
        Raises:
            ReservationNotFound: If reservation doesn't exist
        """
        reservation = await self.reservation_repository.get_by_id(request.reservation_id)
        if not reservation:
            raise ReservationNotFound(f"Reservation {request.reservation_id} not found")
        
        reservation.status = ReservationStatus.CONFIRMED
        await self.reservation_repository.update(reservation)
        return reservation
