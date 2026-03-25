from __future__ import annotations
from pydantic import BaseModel, EmailStr, constr, Field
from typing import Optional


class UserBase(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[constr(strip_whitespace=True, min_length=1, max_length=20)] = None


class UserCreate(UserBase):
    password: constr(strip_whitespace=True, min_length=8)
    role: Optional[str] = Field(default="customer", regex=r"^(customer|staff|admin)$")


class UserUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=100)] = None
    phone: Optional[constr(strip_whitespace=True, min_length=1, max_length=20)] = None
    role: Optional[str] = Field(default=None, regex=r"^(customer|staff|admin)$")


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    force_password_change: bool

    class Config:
        orm_mode = True
