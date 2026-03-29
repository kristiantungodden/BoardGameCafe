from __future__ import annotations
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from features.users.domain.models.user import User


NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PhoneStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
PasswordStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=8)]


class UserBase(BaseModel):
    name: NameStr
    email: EmailStr
    phone: Optional[PhoneStr] = None


class UserCreate(UserBase):
    password: PasswordStr
    role: Optional[str] = Field(default="customer", pattern=r"^(customer|staff|admin)$")


class UserUpdate(BaseModel):
    name: Optional[NameStr] = None
    phone: Optional[PhoneStr] = None
    role: Optional[str] = Field(default=None, pattern=r"^(customer|staff|admin)$")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = Field(pattern=r"^(customer|staff|admin)$")
    force_password_change: bool

    @staticmethod
    def from_domain(user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role.value,
            force_password_change=user.force_password_change,
        )
