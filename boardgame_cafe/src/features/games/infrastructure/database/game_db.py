from shared.infrastructure import db


class GameDB(db.Model):
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

    tag_links = db.relationship(
        "GameTagLinkDB",
        back_populates="game",
        cascade="all, delete-orphan",
    )

    tags = db.relationship(
        "GameTagDB",
        secondary="game_tag_links",
        back_populates="games",
        viewonly=True,
        lazy="selectin",
    )

