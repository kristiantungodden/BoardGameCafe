from flask import Blueprint

bp = Blueprint("games", __name__, url_prefix="/games")

# TODO: Add games routes here

@bp.route("/", methods=["GET"])
def list_games():
    return {"message": "List of games will be here"}, 200

@bp.route("/<int:game_id>", methods=["GET"])
def get_game(game_id):
    return {"message": f"Details for game {game_id} will be here"}, 200