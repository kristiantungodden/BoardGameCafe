import pytest
from features.payments.domain.models.payment import Payment, PaymentStatus


class TestPaymentCreation:
    """Test suite for Payment creation and validation."""
    
    def test_payment_is_created_with_required_fields(self):
        """RULE: A payment can be created with booking_id and amount_cents."""
        payment = Payment(
            booking_id=1,
            amount_cents=32500,
        )

        assert payment.booking_id == 1
        assert payment.amount_cents == 32500
        assert payment.currency == "NOK"
        assert payment.status == PaymentStatus.CALCULATED
        assert payment.provider == "none"
        assert payment.type == "reservation"
        assert payment.provider_ref == "not_created"
        assert payment.created_at is None
        assert payment.id is None
    
    def test_payment_can_be_created_with_all_fields(self):
        """RULE: A payment can be created with all optional fields."""
        from datetime import datetime
        created_at = datetime(2026, 4, 10, 18, 0, 0)
        
        payment = Payment(
            booking_id=1,
            amount_cents=32500,
            id=42,
            currency="NOK",
            status=PaymentStatus.PAID,
            provider="stripe",
            type="payment",
            provider_ref="ch_123456",
            created_at=created_at,
        )

        assert payment.id == 42
        assert payment.currency == "NOK"
        assert payment.status == PaymentStatus.PAID
        assert payment.provider == "stripe"
        assert payment.type == "payment"
        assert payment.provider_ref == "ch_123456"
        assert payment.created_at == created_at
    
    def test_payment_amount_kroner_property(self):
        """RULE: amount_kroner should correctly convert cents to kroner."""
        payment = Payment(booking_id=1, amount_cents=32500)
        assert payment.amount_kroner == 325.0
        
        payment = Payment(booking_id=1, amount_cents=0)
        assert payment.amount_kroner == 0.0
        
        payment = Payment(booking_id=1, amount_cents=1)
        assert payment.amount_kroner == 0.01


class TestPaymentValidation:
    """Test suite for Payment validation rules."""
    
    def test_payment_fails_for_negative_amount(self):
        """RULE: amount_cents cannot be negative."""
        with pytest.raises(ValueError, match="amount_cents cannot be negative"):
            Payment(
                booking_id=1,
                amount_cents=-1,
            )
    
    def test_payment_fails_for_zero_booking_id(self):
        """RULE: booking_id must be positive."""
        with pytest.raises(ValueError, match="booking_id must be positive"):
            Payment(
                booking_id=0,
                amount_cents=1000,
            )
    
    def test_payment_fails_for_negative_booking_id(self):
        """RULE: booking_id must be positive."""
        with pytest.raises(ValueError, match="booking_id must be positive"):
            Payment(
                booking_id=-1,
                amount_cents=1000,
            )
    
    def test_payment_allows_zero_amount(self):
        """RULE: amount_cents can be zero (free booking)."""
        payment = Payment(booking_id=1, amount_cents=0)
        assert payment.amount_cents == 0


class TestPaymentStatusTransitions:
    """Test suite for Payment status transitions."""
    
    def test_payment_created_with_calculated_status(self):
        """RULE: New payments start with CALCULATED status."""
        payment = Payment(booking_id=1, amount_cents=1000)
        assert payment.status == PaymentStatus.CALCULATED
    
    def test_payment_can_have_different_statuses(self):
        """RULE: Payment can be created with different statuses."""
        for status in [PaymentStatus.CALCULATED, PaymentStatus.PENDING, 
                       PaymentStatus.PAID, PaymentStatus.FAILED, PaymentStatus.REFUNDED]:
            payment = Payment(booking_id=1, amount_cents=1000, status=status)
            assert payment.status == status


class TestPaymentSemantics:
    """Test suite for Payment domain semantics."""
    
    def test_payment_default_values(self):
        """RULE: Payment has sensible default values."""
        payment = Payment(booking_id=1, amount_cents=1000)
        
        assert payment.currency == "NOK"
        assert payment.provider == "none"
        assert payment.type == "reservation"
        assert payment.provider_ref == "not_created"
    
    def test_payment_can_update_status(self):
        """RULE: Payment status can be updated after creation."""
        payment = Payment(booking_id=1, amount_cents=1000)
        assert payment.status == PaymentStatus.CALCULATED
        
        payment.status = PaymentStatus.PENDING
        assert payment.status == PaymentStatus.PENDING
        
        payment.status = PaymentStatus.PAID
        assert payment.status == PaymentStatus.PAID
    
    def test_payment_can_update_provider_info(self):
        """RULE: Payment provider information can be updated."""
        payment = Payment(booking_id=1, amount_cents=1000)
        
        payment.provider = "stripe"
        payment.provider_ref = "ch_123456"
        payment.type = "payment"
        
        assert payment.provider == "stripe"
        assert payment.provider_ref == "ch_123456"
        assert payment.type == "payment"
