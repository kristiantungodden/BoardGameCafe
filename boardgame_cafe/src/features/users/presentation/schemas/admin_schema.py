from __future__ import annotations

from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints


NameStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PhoneStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
PasswordStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=8)]


class StewardCreateRequest(BaseModel):
    name: NameStr
    email: EmailStr
    password: PasswordStr
    phone: Optional[PhoneStr] = None


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    force_password_change: bool
