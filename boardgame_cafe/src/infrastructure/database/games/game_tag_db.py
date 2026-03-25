from infrastructure.extensions import db


class GameTag(db.Model):
    __tablename__ = "game_tags"

    id = db.Column(db.Integer, primary_key=True)
<<<<<<< HEAD
    name = db.Column(db.String(50), unique=True, nullable=False)
=======
    name = db.Column(db.String(50), unique=True, nullable=False)

>>>>>>> 6208c66 (error i ref)
