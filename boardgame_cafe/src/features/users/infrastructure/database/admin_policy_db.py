from shared.infrastructure import db


class AdminPolicyDB(db.Model):
    __tablename__ = "admin_policies"

    id = db.Column(db.Integer, primary_key=True)
    booking_base_fee_cents = db.Column(db.Integer, nullable=False, server_default="2500")
    booking_base_fee_override_cents = db.Column(db.Integer, nullable=True)
    booking_base_fee_override_until_epoch = db.Column(db.Integer, nullable=True)
    booking_cancel_time_limit_hours = db.Column(db.Integer, nullable=False, server_default="24")
