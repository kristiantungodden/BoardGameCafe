from flask import Blueprint, request, jsonify
from features.games.domain.models.game import Game
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.games.application.use_cases.game_use_cases import GameUseCases
from decimal import Decimal

bp = Blueprint("games", __name__, url_prefix="/api/games")

# Initialize repository and use case
repository = GameRepository()
use_cases = GameUseCases(repository)


@bp.route("/", methods=["GET"])
def get_games():
    games = use_cases.get_all_games()
    return jsonify([g.__dict__ for g in games]), 200


@bp.route("/<int:game_id>", methods=["GET"])
def get_game(game_id: int):
    game = use_cases.get_game(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(game.__dict__), 200


@bp.route("/", methods=["POST"])
def create_game():
    data = request.json

    # Create a temporary Game object with placeholder ID
    temp_game = Game(
        id=-1,  # placeholder; repository will assign real ID
        title=data["title"],
        min_players=data["min_players"],
        max_players=data["max_players"],
        playtime_min=data["playtime_min"],
        complexity=Decimal(str(data["complexity"])),
        description=data.get("description"),
        image_url=data.get("image_url")
    )

    # Save using use case / repository which will assign the proper ID
    saved_game = use_cases.add_game(temp_game)
    return jsonify(saved_game.__dict__), 201


@bp.route("/<int:game_id>", methods=["PUT"])
def update_game(game_id: int):
    data = request.json
    game = use_cases.get_game(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    # Update fields
    game.title = data.get("title", game.title)
    game.min_players = data.get("min_players", game.min_players)
    game.max_players = data.get("max_players", game.max_players)
    game.playtime_min = data.get("playtime_min", game.playtime_min)
    if "complexity" in data:
        game.complexity = Decimal(str(data["complexity"]))
    game.description = data.get("description", game.description)
    game.image_url = data.get("image_url", game.image_url)

    updated_game = use_cases.update_game(game)
    return jsonify(updated_game.__dict__), 200


@bp.route("/<int:game_id>", methods=["DELETE"])
def delete_game(game_id: int):
    game = use_cases.get_game(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    use_cases.delete_game(game_id)
    return jsonify({"message": "Game deleted"}), 200