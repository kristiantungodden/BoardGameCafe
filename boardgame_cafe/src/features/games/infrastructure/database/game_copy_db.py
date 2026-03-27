from shared.infrastructure import db

class GameCopyDB(db.Model):
    __tablename__ = "game_copies"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    copy_code = db.Column(db.String(50), unique=True, nullable=False)
    condition_note = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), nullable=True)
    updated_at = db.Column(db.DateTime, server_default=db.func.now())

    game = db.relationship("GameDB", backref="copies")