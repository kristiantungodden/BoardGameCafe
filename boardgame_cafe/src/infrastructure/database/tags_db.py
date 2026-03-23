from infrastructure.extensions import db


class GameTag(db.Model):
    __tablename__ = "game_tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)


class GameTagLink(db.Model):
    __tablename__ = "game_tag_links"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    game_tag_id = db.Column(db.Integer, db.ForeignKey("game_tags.id"), nullable=False)

    game = db.relationship("Game", backref="tags")
    tag = db.relationship("GameTag")