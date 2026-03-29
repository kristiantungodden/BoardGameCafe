from abc import ABC, abstractmethod
from typing import Optional

class AuthSessionPortInterface(ABC):
    """Abstract interface for authentication session management."""

    @abstractmethod
    def login(self, user_id: int) -> None:
        """Log in a user by their ID."""
        pass

    @abstractmethod
    def logout(self) -> None:
        """Log out the current user."""
        pass

    @abstractmethod
    def get_current_user_id(self) -> Optional[int]:
        """Get the currently logged-in user's ID, or None if not logged in."""
        pass