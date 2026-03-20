"""Repository interfaces for domain entities."""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
from domain.models import (
    User,
    Game,
    GameCopy,
    Table,
    Reservation,
    Payment,
)


class Repository(ABC):
    """Base repository interface."""
    
    @abstractmethod
    async def add(self, entity) -> None:
        """Add an entity to the repository."""
        pass
    
    @abstractmethod
    async def update(self, entity) -> None:
        """Update an entity in the repository."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: int) -> None:
        """Delete an entity from the repository."""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: int):
        """Get an entity by ID."""
        pass


class UserRepository(Repository, ABC):
    """Repository interface for User entities."""
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pass
    
    @abstractmethod
    async def get_by_role(self, role: str) -> List[User]:
        """Get all users with a specific role."""
        pass


class GameRepository(Repository, ABC):
    """Repository interface for Game entities."""
    
    @abstractmethod
    async def search_by_title(self, title: str) -> List[Game]:
        """Search games by title."""
        pass
    
    @abstractmethod
    async def get_by_tags(self, tags: List[str]) -> List[Game]:
        """Get games by tags."""
        pass


class GameCopyRepository(Repository, ABC):
    """Repository interface for GameCopy entities."""
    
    @abstractmethod
    async def get_by_game_id(self, game_id: int) -> List[GameCopy]:
        """Get all copies of a specific game."""
        pass
    
    @abstractmethod
    async def get_available_copies(self, game_id: int) -> List[GameCopy]:
        """Get available copies of a game."""
        pass


class TableRepository(Repository, ABC):
    """Repository interface for Table entities."""
    
    @abstractmethod
    async def get_by_capacity(self, capacity: int) -> List[Table]:
        """Get tables with at least the specified capacity."""
        pass
    
    @abstractmethod
    async def get_available_tables(self, reserved_at: datetime, reserved_until: datetime, party_size: int) -> List[Table]:
        """Get tables available for a time slot with required capacity."""
        pass


class ReservationRepository(Repository, ABC):
    """Repository interface for Reservation entities."""
    
    @abstractmethod
    async def get_by_customer_id(self, customer_id: int) -> List[Reservation]:
        """Get all reservations for a customer."""
        pass
    
    @abstractmethod
    async def get_by_table_id(self, table_id: int) -> List[Reservation]:
        """Get all reservations for a table."""
        pass
    
    @abstractmethod
    async def get_overlapping(self, table_id: int, reserved_at: datetime, reserved_until: datetime) -> List[Reservation]:
        """Get reservations that overlap with the given time slot."""
        pass


class PaymentRepository(Repository, ABC):
    """Repository interface for Payment entities."""
    
    @abstractmethod
    async def get_by_reservation_id(self, reservation_id: int) -> Optional[Payment]:
        """Get payment for a reservation."""
        pass
    
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> List[Payment]:
        """Get all payments for a user."""
        pass
