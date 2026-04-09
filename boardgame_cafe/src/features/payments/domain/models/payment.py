from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

PRICE_PER_CAPACITY_CENTS = 15000
PRICE_BASE_TABLE = 2500

class PaymentStatus(StrEnum):
    CALCULATED = "calculated"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"



@dataclass
class Payment:
    booking_id: int
    amount_cents: int
    id: int | None = None
    currency: str = "NOK"
    status: PaymentStatus = PaymentStatus.CALCULATED
    provider: str = "none"
    type: str = "reservation"
    provider_ref: str = "not_created"
    created_at: datetime | None = None


    def __post_init__(self) -> None:
        if self.booking_id <= 0:
            raise ValueError("booking_id must be positive")
        if self.amount_cents < 0:
            raise ValueError("amount_cents cannot be negative")

    @property
    def amount_kroner(self) -> float:
        return self.amount_cents / 100.0