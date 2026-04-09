from features.payments.domain.models.payment import PaymentStatus
from typing import Optional


def map_vipps_status_to_payment_status(status: Optional[str]) -> PaymentStatus:
    if not status:
        return PaymentStatus.PENDING

    s = status.upper()
    if s in ("RESERVE", "RESERVED", "SALE", "CAPTURE"):
        return PaymentStatus.PAID
    if s in ("INITIATE",):
        return PaymentStatus.PENDING
    if s in ("CANCEL", "CANCELLED", "REJECTED", "RESERVE_FAILED", "SALE_FAILED"):
        return PaymentStatus.FAILED
    if s in ("REFUND",):
        return PaymentStatus.REFUNDED
    return PaymentStatus.PENDING
