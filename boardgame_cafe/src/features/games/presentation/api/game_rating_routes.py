from flask import Blueprint, request, jsonify
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest

from features.games.application.use_cases.game_rating_use_cases import (
    CreateGameRatingCommand,
)
from features.games.composition.game_use_case_factories import (
    get_game_rating_use_cases,
    rollback_games_transaction,
)
from features.games.domain.models.game_rating import GameRating
from features.games.presentation.schemas.game_rating_schema import (
    GameRatingCreateRequest,
)
from shared.domain.exceptions import DomainError


bp = Blueprint("game_ratings", __name__, url_prefix="/api/game-ratings")

rating_use_cases = get_game_rating_use_cases()


def _serialize_rating(rating: GameRating) -> dict:
    return {
        "id": rating.id,
        "customer_id": rating.customer_id,
        "game_id": rating.game_id,
        "stars": rating.stars,
        "comment": rating.comment,
        "created_at": rating.created_at.isoformat()
        if hasattr(rating.created_at, "isoformat")
        else rating.created_at,
    }


@bp.route("/", methods=["POST"])
def create_rating():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401

    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameRatingCreateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify(
            {
                "error": "Validation failed",
                "details": exc.errors(include_context=False),
            }
        ), 400

    try:
        rating = rating_use_cases.create.execute(
            CreateGameRatingCommand(
                customer_id=current_user.id,
                game_id=payload.game_id,
                stars=payload.stars,
                comment=payload.comment,
            )
        )
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except IntegrityError:
        rollback_games_transaction()
        return jsonify({"error": "User has already rated this game"}), 409

    return jsonify(_serialize_rating(rating)), 201


@bp.route("/game/<int:game_id>", methods=["GET"])
def get_ratings_by_game_id(game_id: int):
    try:
        ratings = rating_use_cases.list_by_game.execute(game_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify([_serialize_rating(r) for r in ratings]), 200


@bp.route("/game/<int:game_id>/average", methods=["GET"])
def get_average_rating(game_id: int):
    try:
        avg = rating_use_cases.get_average.execute(game_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "game_id": game_id,
        "average_rating": avg,
    }), 200