"""Repository interfaces for user management."""

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from features.users.domain.models.user import User


class UserRepositoryInterface(ABC):
    """Abstract interface for user data access."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pass

    @abstractmethod
    def save(self, user: User) -> User:
        """Save user and return with updated ID if new."""
        pass

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Delete user by ID. Returns True if deleted."""
        pass

    @abstractmethod
    def list_all(self) -> Sequence[User]:
        """List all users."""
        pass

    @abstractmethod
    def list_by_role(self, role: str) -> Sequence[User]:
        """List users by role."""
        pass