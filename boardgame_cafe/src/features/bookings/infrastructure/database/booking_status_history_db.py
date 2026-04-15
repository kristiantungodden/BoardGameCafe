from shared.infrastructure import db


class BookingStatusHistoryDB(db.Model):
    __tablename__ = "booking_status_history"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer,
        db.ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status = db.Column(db.String(30), nullable=True)
    to_status = db.Column(db.String(30), nullable=False)
    source = db.Column(db.String(50), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    actor_role = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
