from shared.infrastructure import db

class GameTagLinkDB(db.Model):
    __tablename__ = "game_tag_links"
    __table_args__ = (
        db.UniqueConstraint("game_id", "game_tag_id", name="uq_game_tag_link"),
    )

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    game_tag_id = db.Column(db.Integer, db.ForeignKey("game_tags.id"), nullable=False)

    game = db.relationship("GameDB", backref="tags")
    tag = db.relationship("GameTagDB")