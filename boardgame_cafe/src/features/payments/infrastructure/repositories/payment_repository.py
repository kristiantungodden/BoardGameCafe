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
            table_reservation_id=payment.table_reservation_id,
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
        if self.session is db.session:
            db_payment = PaymentDB.query.get(payment_id)
        else:
            db_payment = self.session.get(PaymentDB, payment_id)
        if db_payment is None:
            return None
        return db_payment.to_domain()
