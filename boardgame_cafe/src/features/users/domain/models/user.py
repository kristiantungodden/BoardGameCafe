from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import re
from enum import Enum

from shared.domain.exceptions import ValidationError


class Role(str, Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"


@dataclass
class User:
    """
    Business rules and validation for user management.
    Password hashing/verification belongs and is implemented in the infrastructure layer.
    """
    name: str
    email: str
    password_hash: str  # Pre-hashed password from infrastructure
    role: Role = Role.CUSTOMER
    force_password_change: bool = False
    is_suspended: bool = False
    phone: Optional[str] = None
    id: Optional[int] = None

    def __post_init__(self) -> None:
        """Validate user data after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate user business rules."""
        if not self.name or len(self.name.strip()) == 0:
            raise ValidationError("Name cannot be empty")
        if not self.email or not re.match(r"[^@]+@[^@]+\.[^@]+", self.email):
            raise ValidationError("Invalid email address")
        if not self.password_hash:
            raise ValidationError("Password hash cannot be empty")
        if len(self.name.strip()) > 100:
            raise ValidationError("Name cannot exceed 100 characters")
        if len(self.email) > 255:
            raise ValidationError("Email cannot exceed 255 characters")
        if self.phone and len(self.phone) > 20:
            raise ValidationError("Phone number cannot exceed 20 characters")

    def change_password(self, new_password_hash: str) -> None:
        """Change user's password hash."""
        if not new_password_hash:
            raise ValidationError("New password hash cannot be empty")
        self.password_hash = new_password_hash
        self.force_password_change = False

    def force_password_reset(self) -> None:
        """Force user to change password on next login."""
        self.force_password_change = True

    def suspend(self) -> None:
        """Suspend account access until explicitly restored."""
        self.is_suspended = True

    def unsuspend(self) -> None:
        """Restore account access for a suspended user."""
        self.is_suspended = False

    def update_profile(self, name: Optional[str] = None, phone: Optional[str] = None) -> None:
        """Update user profile information."""
        original_name = self.name
        original_phone = self.phone

        if name is not None:
            self.name = name
        if phone is not None:
            self.phone = phone

        try:
            self._validate()  # Re-validate after changes
        except ValidationError:
            # Keep updates atomic: invalid changes must not mutate persisted state.
            self.name = original_name
            self.phone = original_phone
            raise

    def can_access_admin_features(self) -> bool:
        """Check if user has admin privileges."""
        return self.role in (Role.ADMIN, Role.STAFF)

    def is_admin(self) -> bool:
        """Check if user is an administrator."""
        return self.role == Role.ADMIN

    def is_staff(self) -> bool:
        """Check if user is staff."""
        return self.role == Role.STAFF

    def is_customer(self) -> bool:
        """Check if user is a customer."""
        return self.role == Role.CUSTOMER


