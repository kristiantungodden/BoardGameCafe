from decimal import Decimal

from flask import Blueprint, request, jsonify
from pydantic import ValidationError as PydanticValidationError
from werkzeug.exceptions import BadRequest

from features.games.application.use_cases.game_use_cases import GameUseCases
from features.games.domain.models.game import Game
from features.games.infrastructure.repositories.game_repository import GameRepository
from features.games.presentation.schemas.game_schema import (
    GameCreateRequest,
    GameUpdateRequest,
)

bp = Blueprint("games", __name__, url_prefix="/api/games")

# Initialize repository and use case
repository = GameRepository()
use_cases = GameUseCases(repository)


def _serialize_game(game: Game) -> dict:
    return {
        "id": game.id,
        "title": game.title,
        "min_players": game.min_players,
        "max_players": game.max_players,
        "playtime_min": game.playtime_min,
        "complexity": float(game.complexity),
        "description": game.description,
        "image_url": game.image_url,
        "created_at": game.created_at.isoformat()
        if hasattr(game.created_at, "isoformat")
        else game.created_at,
    }


@bp.route("/", methods=["GET"])
def get_games():
    games = use_cases.get_all_games()
    return jsonify([_serialize_game(g) for g in games]), 200


@bp.route("/<int:game_id>", methods=["GET"])
def get_game(game_id: int):
    game = use_cases.get_game(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(_serialize_game(game)), 200


@bp.route("/", methods=["POST"])
def create_game():
    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameCreateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors(include_context=False)}), 400

    temp_game = Game(
        id=None,
        title=payload.title,
        min_players=payload.min_players,
        max_players=payload.max_players,
        playtime_min=payload.playtime_min,
        complexity=payload.complexity,
        description=payload.description,
        image_url=payload.image_url,
    )

    saved_game = use_cases.add_game(temp_game)
    return jsonify(_serialize_game(saved_game)), 201


@bp.route("/<int:game_id>", methods=["PUT"])
def update_game(game_id: int):
    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameUpdateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors(include_context=False)}), 400

    if payload.model_dump(exclude_none=True) == {}:
        return jsonify({"error": "At least one field must be provided"}), 400

    game = use_cases.get_game(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    new_title = payload.title if payload.title is not None else game.title
    new_min_players = (
        payload.min_players if payload.min_players is not None else game.min_players
    )
    new_max_players = (
        payload.max_players if payload.max_players is not None else game.max_players
    )
    new_playtime_min = (
        payload.playtime_min if payload.playtime_min is not None else game.playtime_min
    )
    new_complexity = payload.complexity if payload.complexity is not None else game.complexity
    new_description = payload.description if payload.description is not None else game.description
    new_image_url = payload.image_url if payload.image_url is not None else game.image_url

    game.update_details(
        title=new_title,
        min_players=new_min_players,
        max_players=new_max_players,
        playtime_min=new_playtime_min,
        complexity=new_complexity,
        description=new_description,
        image_url=new_image_url,
    )

    updated_game = use_cases.update_game(game)
    return jsonify(_serialize_game(updated_game)), 200


@bp.route("/<int:game_id>", methods=["DELETE"])
def delete_game(game_id: int):
    game = use_cases.get_game(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    use_cases.delete_game(game_id)
    return jsonify({"message": "Game deleted"}), 200