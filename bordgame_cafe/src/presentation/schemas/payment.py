"""Payment schema."""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel


class PaymentBase(BaseModel):
    """Base payment schema."""
    amount: Decimal
    currency: str = "USD"
    payment_type: str
    status: str = "pending"
    provider: str = "stripe"
    description: Optional[str] = None


class PaymentCreate(BaseModel):
    """Schema for creating a payment."""
    reservation_id: Optional[int] = None
    amount: Decimal
    currency: str = "USD"
    payment_type: str
    description: Optional[str] = None


class PaymentUpdate(BaseModel):
    """Schema for updating a payment."""
    status: Optional[str] = None
    provider_transaction_id: Optional[str] = None


class PaymentResponse(PaymentBase):
    """Schema for payment response."""
    id: int
    reservation_id: Optional[int] = None
    user_id: int
    provider_transaction_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
