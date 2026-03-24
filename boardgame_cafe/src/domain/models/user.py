from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import re
from ..services.password_service import hash_password

@dataclass
class User:
    id: int
    email: str
    hashed_password: str
    is_active: bool = True

    def set_password(self, raw_password: str):
        # hash here or through werkgezeug service
        self.hashed_password = hash_password(raw_password)

    def validate_email(self):
        return NotImplementedError("Email validation not implemented yet")
    def can_reserve(self):
        return NotImplementedError("User reservation eligibility not implemented yet")
    def is_email_verifid(self):
        return NotImplementedError("Email verification status not implemented yet")
