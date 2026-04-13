from shared.infrastructure import db


class GameRatingDB(db.Model):
    __tablename__ = "game_ratings"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    stars = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    customer = db.relationship("UserDB", backref="ratings")
    game = db.relationship("GameDB")

    __table_args__ = (
        db.CheckConstraint("stars >= 1 AND stars <= 5", name="check_stars_between_1_and_5"),
        db.UniqueConstraint("customer_id", "game_id", name="unique_customer_game_rating"),
    )