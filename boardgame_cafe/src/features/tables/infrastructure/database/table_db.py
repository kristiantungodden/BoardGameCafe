from shared.infrastructure import db


class TableDB(db.Model):
    __tablename__ = "cafe_tables"

    id = db.Column(db.Integer, primary_key=True)
    table_nr = db.Column(db.String(10), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    floor = db.Column(db.Integer, nullable=False, default=1)
    zone = db.Column(db.String(50), nullable=False)
    price_cents = db.Column(db.Integer, nullable=False, default=15000)
    features = db.Column(db.JSON, default=dict)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    rotation = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False)