"""Payment domain model."""

from enum import Enum
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel


class PaymentStatus(str, Enum):
    """Status of a payment."""
    
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentType(str, Enum):
    """Type of payment."""
    
    RESERVATION_FEE = "reservation_fee"
    LATE_FEE = "late_fee"
    DAMAGE_FEE = "damage_fee"
    REFUND = "refund"


class Payment(BaseModel):
    """Payment entity."""
    
    id: Optional[int] = None
    reservation_id: Optional[int] = None
    user_id: int
    amount: Decimal
    currency: str = "USD"
    payment_type: PaymentType
    status: PaymentStatus = PaymentStatus.PENDING
    provider: str = "stripe"  # payment provider
    provider_transaction_id: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True

    def __str__(self) -> str:
        return f"Payment {self.id} - {self.amount} {self.currency} - {self.status}"
