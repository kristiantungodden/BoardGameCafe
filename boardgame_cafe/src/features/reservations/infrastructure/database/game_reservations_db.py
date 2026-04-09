from shared.infrastructure import db


class GameReservationDB(db.Model):
    __tablename__ = "game_reservations"
    __table_args__ = (
        db.UniqueConstraint(
            "booking_id",
            "game_copy_id",
            name="uq_game_reservation_copy_per_booking",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(
        db.Integer, db.ForeignKey("bookings.id"), nullable=False
    )
    game_copy_id = db.Column(
        db.Integer, db.ForeignKey("game_copies.id"), nullable=False
    )
    requested_game_id = db.Column(
        db.Integer, db.ForeignKey("games.id"), nullable=False
    )

    game_copy = db.relationship("GameCopyDB")
    requested_game = db.relationship("GameDB")