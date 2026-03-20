"""User domain model."""

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    """User roles in the system."""
    
    CUSTOMER = "customer"
    STEWARD = "steward"
    ADMIN = "admin"


class User(BaseModel):
    """User entity."""
    
    id: Optional[int] = None
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    password_hash: str
    role: UserRole = UserRole.CUSTOMER
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"
