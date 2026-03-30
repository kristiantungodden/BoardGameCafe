from shared.infrastructure import db


class GameReservationDB(db.Model):
    __tablename__ = "game_reservations"
    __table_args__ = (
        db.UniqueConstraint(
            "table_reservation_id",
            "game_copy_id",
            name="uq_game_reservation_copy_per_booking",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    table_reservation_id = db.Column(
        db.Integer, db.ForeignKey("table_reservations.id"), nullable=False
    )
    game_copy_id = db.Column(
        db.Integer, db.ForeignKey("game_copies.id"), nullable=False
    )
    requested_game_id = db.Column(
        db.Integer, db.ForeignKey("games.id"), nullable=False
    )

    table_reservation = db.relationship("TableReservationDB", backref="game_reservations")
    game_copy = db.relationship("GameCopyDB")
    requested_game = db.relationship("GameDB")