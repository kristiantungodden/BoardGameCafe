"""Game-related use cases."""

from datetime import datetime
from pydantic import BaseModel
from domain.models import GameCopy, GameCopyStatus
from domain.exceptions import GameCopyNotFound, ReservationNotFound


class AssignGameToReservationRequest(BaseModel):
    """Request for assigning a game to a reservation."""
    
    game_copy_id: int
    reservation_id: int
    assigned_by: int


class AssignGameToReservationUseCase:
    """Use case for assigning a game copy to a reservation."""
    
    def __init__(self, game_copy_repository, reservation_repository) -> None:
        self.game_copy_repository = game_copy_repository
        self.reservation_repository = reservation_repository
    
    async def execute(self, request: AssignGameToReservationRequest) -> GameCopy:
        """
        Assign a game copy to a reservation.
        
        Args:
            request: Assignment request
            
        Returns:
            Updated game copy
            
        Raises:
            GameCopyNotFound: If game copy doesn't exist
            ReservationNotFound: If reservation doesn't exist
        """
        game_copy = await self.game_copy_repository.get_by_id(request.game_copy_id)
        if not game_copy:
            raise GameCopyNotFound(f"Game copy {request.game_copy_id} not found")
        
        reservation = await self.reservation_repository.get_by_id(request.reservation_id)
        if not reservation:
            raise ReservationNotFound(f"Reservation {request.reservation_id} not found")
        
        game_copy.status = GameCopyStatus.RESERVED
        await self.game_copy_repository.update(game_copy)
        return game_copy


class CheckoutGameRequest(BaseModel):
    """Request for checking out a game."""
    
    game_copy_id: int
    reservation_id: int
    checked_out_by: int


class CheckoutGameUseCase:
    """Use case for checking out a game copy."""
    
    def __init__(self, game_copy_repository) -> None:
        self.game_copy_repository = game_copy_repository
    
    async def execute(self, request: CheckoutGameRequest) -> GameCopy:
        """
        Check out a game copy.
        
        Args:
            request: Checkout request
            
        Returns:
            Updated game copy
            
        Raises:
            GameCopyNotFound: If game copy doesn't exist
        """
        game_copy = await self.game_copy_repository.get_by_id(request.game_copy_id)
        if not game_copy:
            raise GameCopyNotFound(f"Game copy {request.game_copy_id} not found")
        
        game_copy.status = GameCopyStatus.CHECKED_OUT
        await self.game_copy_repository.update(game_copy)
        return game_copy


class ReturnGameRequest(BaseModel):
    """Request for returning a game."""
    
    game_copy_id: int
    reservation_id: int
    returned_by: int


class ReturnGameUseCase:
    """Use case for returning a game copy."""
    
    def __init__(self, game_copy_repository) -> None:
        self.game_copy_repository = game_copy_repository
    
    async def execute(self, request: ReturnGameRequest) -> GameCopy:
        """
        Return a game copy.
        
        Args:
            request: Return request
            
        Returns:
            Updated game copy
            
        Raises:
            GameCopyNotFound: If game copy doesn't exist
        """
        game_copy = await self.game_copy_repository.get_by_id(request.game_copy_id)
        if not game_copy:
            raise GameCopyNotFound(f"Game copy {request.game_copy_id} not found")
        
        game_copy.status = GameCopyStatus.AVAILABLE
        await self.game_copy_repository.update(game_copy)
        return game_copy
