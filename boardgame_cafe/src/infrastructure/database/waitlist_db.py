from infrastructure.extensions import db


class WaitlistEntry(db.Model):
    __tablename__ = "waitlist_entries"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    desired_start = db.Column(db.DateTime, nullable=False)
    desired_end = db.Column(db.DateTime, nullable=False)

    party_size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(20), nullable=False)

    customer = db.relationship("User", backref="waitlist")