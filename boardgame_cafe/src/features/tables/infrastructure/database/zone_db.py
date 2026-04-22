from shared.infrastructure import db


class ZoneDB(db.Model):
    __tablename__ = "cafe_zones"
    __table_args__ = (
        db.UniqueConstraint("floor", "name", name="uq_cafe_zones_floor_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    floor = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    notes = db.Column(db.Text, nullable=True)
