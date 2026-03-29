from __future__ import annotations
from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints

PasswordStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

class LoginRequest(BaseModel):
    email: EmailStr
    password: PasswordStr
