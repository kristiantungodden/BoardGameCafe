from shared.infrastructure import db


class FloorDB(db.Model):
    __tablename__ = "cafe_floors"

    id = db.Column(db.Integer, primary_key=True)
    floor_nr = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text, nullable=True)