"""Payment domain events."""

from datetime import datetime
from decimal import Decimal
from .domain_event import DomainEvent


class PaymentCaptured(DomainEvent):
    """Raised when a payment is successfully captured."""
    
    user_id: int
    amount: Decimal
    currency: str
    payment_type: str
    captured_at: datetime
