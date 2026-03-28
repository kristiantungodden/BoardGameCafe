from features.payments.application.interfaces.payment_repository_interface import (
    PaymentRepositoryInterface,
)
from features.payments.domain.models.payment import Payment as DomainPayment
from features.payments.infrastructure.database.payments_db import PaymentDB
from shared.infrastructure import db


class PaymentRepository(PaymentRepositoryInterface):
    def add(self, payment: DomainPayment) -> DomainPayment:
        db_payment = PaymentDB(
            table_reservation_id=payment.table_reservation_id,
            type=payment.type,
            provider=payment.provider,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            status=payment.status,
            provider_ref=payment.provider_ref,
        )
        db.session.add(db_payment)
        db.session.commit()
        return db_payment.to_domain()

    def get_by_id(self, payment_id: int) -> DomainPayment | None:
        db_payment = PaymentDB.query.get(payment_id)
        if db_payment is None:
            return None
        return db_payment.to_domain()
