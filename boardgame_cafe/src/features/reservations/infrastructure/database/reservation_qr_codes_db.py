from shared.infrastructure import db


class ReservationQRCodeDB(db.Model):
    __tablename__ = "reservation_qr_codes"
    __table_args__ = (
        db.UniqueConstraint("reservation_id", name="uq_reservation_qr_reservation"),
        db.UniqueConstraint("qr_code", name="uq_reservation_qr_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    reservation_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id"),
        nullable=False,
        index=True,
    )
    qr_code = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    user = db.relationship("UserDB")
    reservation = db.relationship("BookingDB")
