from flask import Blueprint, request, jsonify
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest

from features.games.application.use_cases.game_rating_use_cases import (
    CreateGameRatingCommand,
    CreateGameRatingUseCase,
    GetRatingsByGameIdUseCase,
    GetAverageRatingByGameIdUseCase,
)
from features.games.domain.models.game_rating import GameRating
from features.games.infrastructure.repositories.game_rating_repository import (
    GameRatingRepositoryImpl,
)
from features.games.presentation.schemas.game_rating_schema import (
    GameRatingCreateRequest,
)
from shared.domain.exceptions import DomainError
from shared.infrastructure import db


bp = Blueprint("game_ratings", __name__, url_prefix="/api/game-ratings")

repository = GameRatingRepositoryImpl()

create_game_rating_use_case = CreateGameRatingUseCase(repository)
get_ratings_by_game_id_use_case = GetRatingsByGameIdUseCase(repository)
get_average_rating_use_case = GetAverageRatingByGameIdUseCase(repository)


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
        rating = create_game_rating_use_case.execute(
            CreateGameRatingCommand(
                customer_id=payload.customer_id,
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
        db.session.rollback()
        return jsonify({"error": "User has already rated this game"}), 409

    return jsonify(_serialize_rating(rating)), 201


@bp.route("/game/<int:game_id>", methods=["GET"])
def get_ratings_by_game_id(game_id: int):
    try:
        ratings = get_ratings_by_game_id_use_case.execute(game_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify([_serialize_rating(r) for r in ratings]), 200


@bp.route("/game/<int:game_id>/average", methods=["GET"])
def get_average_rating(game_id: int):
    try:
        avg = get_average_rating_use_case.execute(game_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "game_id": game_id,
        "average_rating": avg,
    }), 200