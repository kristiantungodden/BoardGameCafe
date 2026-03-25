from infrastructure.extensions import db


class GameTag(db.Model):
    __tablename__ = "game_tags"

    id = db.Column(db.Integer, primary_key=True)
<<<<<<< HEAD
    name = db.Column(db.String(50), unique=True, nullable=False)
=======
    name = db.Column(db.String(50), unique=True, nullable=False)

<<<<<<< HEAD
=======
>>>>>>> 6208c66 (error i ref)
>>>>>>> c06a22558df69a6d68c380df4c4764b99367013b
