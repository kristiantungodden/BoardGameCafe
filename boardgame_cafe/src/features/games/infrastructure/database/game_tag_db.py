from shared.infrastructure import db


class GameTagDB(db.Model):
    __tablename__ = "game_tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    tag_links = db.relationship(
        "GameTagLinkDB",
        back_populates="tag",
        cascade="all, delete-orphan",
    )

    games = db.relationship(
        "GameDB",
        secondary="game_tag_links",
        back_populates="tags",
        viewonly=True,
        lazy="selectin",
    )
