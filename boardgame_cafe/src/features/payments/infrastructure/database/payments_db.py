from shared.infrastructure import db
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

    def to_domain(self) -> DomainPayment:
        return DomainPayment(
            id=self.id,
            table_reservation_id=self.table_reservation_id,
            type=self.type,
            provider=self.provider,
            amount_cents=self.amount_cents,
            currency=self.currency,
            status=self.status,
            provider_ref=self.provider_ref,
            created_at=self.created_at,
        )