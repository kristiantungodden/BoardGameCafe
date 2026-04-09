from features.payments.infrastructure.vipps.vipps_mapper import map_vipps_status_to_payment_status
from features.payments.domain.models.payment import PaymentStatus


def test_mapper_various_statuses():
    assert map_vipps_status_to_payment_status("RESERVE") == PaymentStatus.PAID
    assert map_vipps_status_to_payment_status("INITIATE") == PaymentStatus.PENDING
    assert map_vipps_status_to_payment_status("CANCELLED") == PaymentStatus.FAILED
    assert map_vipps_status_to_payment_status("REFUND") == PaymentStatus.REFUNDED
    assert map_vipps_status_to_payment_status(None) == PaymentStatus.PENDING
