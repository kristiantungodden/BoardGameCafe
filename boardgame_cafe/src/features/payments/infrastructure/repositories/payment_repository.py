from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.domain.models.payment import Payment as DomainPayment
from features.payments.infrastructure.database.payments_db import PaymentDB
from shared.infrastructure import db
from sqlalchemy.orm import Session


class PaymentRepository(PaymentRepositoryInterface):
    def __init__(self, session: Session | None = None, auto_commit: bool = True):
        self.session = session or db.session
        self.auto_commit = auto_commit

    def add(self, payment: DomainPayment) -> DomainPayment:
        db_payment = PaymentDB(
            booking_id=payment.booking_id,
            type=payment.type,
            provider=payment.provider,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            status=payment.status,
            provider_ref=payment.provider_ref,
        )
        self.session.add(db_payment)
        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()
        return db_payment.to_domain()

    def get_by_id(self, payment_id: int) -> DomainPayment | None:
        try:
            db_payment = self.session.get(PaymentDB, payment_id)
        except RuntimeError:
            # Fallback for contexts where scoped session isn't bound (tests)
            db_payment = PaymentDB.query.get(payment_id)
        if db_payment is None:
            return None
        return db_payment.to_domain()

    def get_by_booking_id(self, booking_id: int) -> DomainPayment | None:
        db_payment = self.session.query(PaymentDB).filter_by(
            booking_id=booking_id
        ).first()
        if db_payment is None:
            return None
        return db_payment.to_domain()

    def get_by_provider_ref(self, provider_ref: str) -> DomainPayment | None:
        db_payment = self.session.query(PaymentDB).filter_by(provider_ref=provider_ref).first()
        if db_payment is None:
            return None
        return db_payment.to_domain()

    def update(self, payment: DomainPayment) -> DomainPayment:
        if payment.id is None:
            raise ValueError("Cannot update payment without id")

        try:
            db_payment = self.session.get(PaymentDB, payment.id)
        except RuntimeError:
            # Fallback for contexts where scoped session isn't bound (tests)
            db_payment = PaymentDB.query.get(payment.id)

        if db_payment is None:
            raise ValueError(f"Payment with id {payment.id} not found")

        db_payment.booking_id = payment.booking_id
        db_payment.type = payment.type
        db_payment.provider = payment.provider
        db_payment.amount_cents = payment.amount_cents
        db_payment.currency = payment.currency
        db_payment.status = payment.status
        db_payment.provider_ref = payment.provider_ref

        if self.auto_commit:
            self.session.commit()
        else:
            self.session.flush()

        return db_payment.to_domain()
