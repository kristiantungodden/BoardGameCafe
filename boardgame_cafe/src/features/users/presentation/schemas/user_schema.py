from __future__ import annotations
from typing import Annotated, Optional
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from features.users.domain.models.user import User


NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PhoneStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
PasswordStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=8)]


class UserBase(BaseModel):
    name: NameStr
    email: EmailStr
    phone: Optional[PhoneStr] = None

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_empty_phone(cls, value):
        # HTML forms submit empty optional fields as "", but our domain expects None.
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class UserCreate(UserBase):
    password: PasswordStr
    role: Optional[str] = Field(default="customer", pattern=r"^(customer|staff|admin)$")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        # Registration policy: minimum 8 chars with at least one letter and one digit.
        if (
            not re.search(r"[A-Za-z]", value)
            or not re.search(r"\d", value)
        ):
            raise ValueError(
                "Password must include at least one letter and one digit"
            )
        return value


class UserUpdate(BaseModel):
    name: Optional[NameStr] = None
    phone: Optional[PhoneStr] = None
    role: Optional[str] = Field(default=None, pattern=r"^(customer|staff|admin)$")

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_empty_phone(cls, value):
        # Allow HTML form submissions to clear optional phone values.
        if isinstance(value, str) and value.strip() == "":
            return None
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str = Field(pattern=r"^(customer|staff|admin)$")
    force_password_change: bool
    is_suspended: bool

    @staticmethod
    def from_domain(user: User) -> UserResponse:
        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            role=user.role.value,
            force_password_change=user.force_password_change,
            is_suspended=bool(getattr(user, "is_suspended", False)),
        )
