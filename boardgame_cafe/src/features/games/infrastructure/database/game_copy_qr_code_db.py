from shared.infrastructure import db


class GameCopyQRCodeDB(db.Model):
    __tablename__ = "game_copy_qr_codes"
    __table_args__ = (
        db.UniqueConstraint("game_copy_id", name="uq_game_copy_qr_game_copy"),
        db.UniqueConstraint("qr_code", name="uq_game_copy_qr_token"),
    )

    id = db.Column(db.Integer, primary_key=True)
    game_copy_id = db.Column(
        db.Integer,
        db.ForeignKey("game_copies.id"),
        nullable=False,
        index=True,
    )
    qr_code = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    game_copy = db.relationship("GameCopyDB")