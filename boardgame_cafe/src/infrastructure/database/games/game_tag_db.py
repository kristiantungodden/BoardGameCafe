from infrastructure.extensions import db


class GameTag(db.Model):
    __tablename__ = "game_tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
