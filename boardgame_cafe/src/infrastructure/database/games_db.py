from infrastructure.extensions import db


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    min_players = db.Column(db.Integer, nullable=False)
    max_players = db.Column(db.Integer, nullable=False)
    playtime_min = db.Column(db.Integer, nullable=False)
    complexity = db.Column(db.Numeric(3, 2), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class GameCopy(db.Model):
    __tablename__ = "game_copies"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    copy_code = db.Column(db.String(50), unique=True, nullable=False)
    condition_note = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now())

    game = db.relationship("Game", backref="copies")