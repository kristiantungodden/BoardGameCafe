from abc import ABC, abstractmethod

class PasswordHasherInterface(ABC):
    """Abstract interface for password hashing."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hash a plaintext password."""
        pass

    @abstractmethod
    def verify(self, hashed: str, password: str) -> bool:
        """Verify a plaintext password against a hashed version."""
        pass