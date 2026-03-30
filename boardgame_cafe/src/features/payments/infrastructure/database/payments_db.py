from shared.infrastructure import db
from features.payments.application.interfaces.payment_repository_interface import PaymentRepositoryInterface as PaymentRepository
from features.payments.domain.models.payment import Payment as DomainPayment


class PaymentDB(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    table_reservation_id = db.Column(
        db.Integer, db.ForeignKey("table_reservations.id"), nullable=False
    )

    type = db.Column(db.String(50), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    amount_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), default="NOK")
    status = db.Column(db.String(20), nullable=False)
    provider_ref = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    table_reservation = db.relationship("TableReservationDB", backref="payments")

  


class PaymentsRepositoryDB(PaymentRepository):
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
        return payment