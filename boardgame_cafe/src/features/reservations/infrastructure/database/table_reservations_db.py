from shared.infrastructure import db


class TableReservationDB(db.Model):
    __tablename__ = "table_reservations"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    start_ts = db.Column(db.DateTime, nullable=True)
    end_ts = db.Column(db.DateTime, nullable=True)
    party_size = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(30), nullable=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey("cafe_tables.id"), nullable=False)

    booking = db.relationship("BookingDB")
    table = db.relationship("TableDB", backref="reservations")