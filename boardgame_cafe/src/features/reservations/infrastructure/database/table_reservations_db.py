from shared.infrastructure import db


class TableReservationDB(db.Model):
    __tablename__ = "table_reservations"
    __table_args__ = (
        db.CheckConstraint("party_size > 0", name="ck_table_reservations_party_size_positive"),
        db.CheckConstraint("end_ts > start_ts", name="ck_table_reservations_time_window"),
        db.CheckConstraint(
            "status IN ('confirmed', 'seated', 'completed', 'cancelled', 'no_show')",
            name="ck_table_reservations_status_valid",
        ),
    )

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