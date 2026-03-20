"""Payment-related use cases."""

from decimal import Decimal
from pydantic import BaseModel
from domain.models import Payment, PaymentStatus, PaymentType
from domain.exceptions import ReservationNotFound, PaymentProcessingError
from infrastructure.payment.vipps import get_payment_provider


class ProcessPaymentRequest(BaseModel):
    """Request for processing a payment."""
    
    user_id: int
    reservation_id: int
    amount: Decimal
    payment_type: PaymentType
    currency: str = "NOK"


class ProcessPaymentUseCase:
    """Use case for processing a payment."""
    
    def __init__(self, payment_repository, reservation_repository) -> None:
        self.payment_repository = payment_repository
        self.reservation_repository = reservation_repository
        self.payment_provider = get_payment_provider()
    
    async def execute(self, request: ProcessPaymentRequest) -> Payment:
        """
        Process a payment for a reservation or fee.
        
        Args:
            request: Payment request
            
        Returns:
            Created/updated payment
            
        Raises:
            ReservationNotFound: If reservation doesn't exist
            PaymentProcessingError: If payment processing fails
        """
        if request.reservation_id:
            reservation = await self.reservation_repository.get_by_id(
                request.reservation_id
            )
            if not reservation:
                raise ReservationNotFound(
                    f"Reservation {request.reservation_id} not found"
                )
        
        # Create payment record
        payment = Payment(
            user_id=request.user_id,
            reservation_id=request.reservation_id,
            amount=request.amount,
            currency=request.currency,
            payment_type=request.payment_type,
            status=PaymentStatus.PENDING,
        )
        
        # Call Vipps payment provider
        reference = f"RES-{request.reservation_id}-{request.user_id}"
        description = f"Reservation {request.reservation_id} - {request.payment_type.value}"
        
        provider_response = self.payment_provider.charge(
            amount=request.amount,
            customer_id=request.user_id,
            reference=reference,
            description=description,
        )
        
        if not provider_response.get('success'):
            raise PaymentProcessingError(
                f"Payment processing failed: {provider_response.get('error')}"
            )
        
        payment.provider_transaction_id = provider_response['transaction_id']
        payment.status = PaymentStatus.PROCESSING
        
        await self.payment_repository.add(payment)
        return payment
