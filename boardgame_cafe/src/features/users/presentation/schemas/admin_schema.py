from __future__ import annotations

from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints


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


class PricingBaseFeeUpdateRequest(BaseModel):
    booking_base_fee_cents: int = Field(ge=0)
    booking_base_fee_priority: int = Field(default=0, ge=0)
    booking_cancel_time_limit_hours: int = Field(default=24, ge=0)
    booking_base_fee_active_until: Optional[str] = None


class PricingItemUpdateRequest(BaseModel):
    price_cents: int = Field(ge=0)


class AnnouncementCreateRequest(BaseModel):
    title: str
    body: str
    cta_label: Optional[str] = None
    cta_url: Optional[str] = None
    publish_now: bool = False


class AnnouncementUpdateRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    cta_label: Optional[str] = None
    cta_url: Optional[str] = None


class SuspensionUpdateRequest(BaseModel):
    suspended: bool
