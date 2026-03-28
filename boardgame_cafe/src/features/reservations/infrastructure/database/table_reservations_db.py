from shared.infrastructure import db


class TableReservation(db.Model):
    __tablename__ = "table_reservations"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey("cafe_tables.id"), nullable=False)

    start_ts = db.Column(db.DateTime, nullable=False)
    end_ts = db.Column(db.DateTime, nullable=False)
    party_size = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    customer = db.relationship("UserDB", backref="reservations")
    table = db.relationship("TableDB", backref="reservations")