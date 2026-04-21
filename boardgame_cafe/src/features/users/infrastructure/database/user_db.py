from shared.infrastructure import db
from flask_login import UserMixin


class UserDB(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, default="customer")
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.Text, nullable=False)
    force_password_change = db.Column(db.Boolean, nullable=False, default=False)
    is_suspended = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "force_password_change": self.force_password_change,
            "is_suspended": self.is_suspended,
        }
