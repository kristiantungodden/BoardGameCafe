from flask import Blueprint, request, jsonify
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest

from features.games.application.use_cases.game_copy_use_cases import (
    CreateGameCopyCommand,
    CreateGameCopyUseCase,
    GetGameCopyByIdUseCase,
    ListGameCopiesUseCase,
    UpdateGameCopyConditionNoteUseCase,
    UpdateGameCopyLocationUseCase,
    UpdateGameCopyStatusUseCase,
)
from features.games.domain.models.game_copy import GameCopy
from features.games.infrastructure.repositories.game_copy_repository import (
    GameCopyRepositoryImpl,
)
from features.games.presentation.schemas.game_copy_schema import (
    GameCopyConditionNoteUpdateRequest,
    GameCopyCreateRequest,
    GameCopyLocationUpdateRequest,
    GameCopyStatusUpdateRequest,
)
from shared.domain.exceptions import DomainError
from shared.infrastructure import db

bp = Blueprint("game_copies", __name__, url_prefix="/api/game-copies")

repository = GameCopyRepositoryImpl()
create_game_copy_use_case = CreateGameCopyUseCase(repository)
list_game_copies_use_case = ListGameCopiesUseCase(repository)
get_game_copy_by_id_use_case = GetGameCopyByIdUseCase(repository)
update_game_copy_status_use_case = UpdateGameCopyStatusUseCase(repository)
update_game_copy_location_use_case = UpdateGameCopyLocationUseCase(repository)
update_game_copy_condition_note_use_case = UpdateGameCopyConditionNoteUseCase(repository)


def _serialize_game_copy(game_copy: GameCopy) -> dict:
    return {
        "id": game_copy.id,
        "game_id": game_copy.game_id,
        "copy_code": game_copy.copy_code,
        "status": game_copy.status,
        "location": game_copy.location,
        "condition_note": game_copy.condition_note,
        "updated_at": game_copy.updated_at.isoformat()
        if hasattr(game_copy.updated_at, "isoformat")
        else game_copy.updated_at,
    }


@bp.route("/", methods=["GET"])
def list_game_copies():
    game_copies = list_game_copies_use_case.execute()
    return jsonify([_serialize_game_copy(copy) for copy in game_copies]), 200


@bp.route("/<int:copy_id>", methods=["GET"])
def get_game_copy(copy_id: int):
    game_copy = get_game_copy_by_id_use_case.execute(copy_id)
    if not game_copy:
        return jsonify({"error": "Game copy not found"}), 404

    return jsonify(_serialize_game_copy(game_copy)), 200


@bp.route("/", methods=["POST"])
def create_game_copy():
    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameCopyCreateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify(
            {
                "error": "Validation failed",
                "details": exc.errors(include_context=False),
            }
        ), 400

    try:
        game_copy = create_game_copy_use_case.execute(
            CreateGameCopyCommand(
                game_id=payload.game_id,
                copy_code=payload.copy_code,
                status=payload.status,
                location=payload.location,
                condition_note=payload.condition_note,
            )
        )
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "copy_code already exists"}), 409

    return jsonify(_serialize_game_copy(game_copy)), 201


@bp.route("/<int:copy_id>/status", methods=["PATCH"])
def update_game_copy_status(copy_id: int):
    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameCopyStatusUpdateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify(
            {
                "error": "Validation failed",
                "details": exc.errors(include_context=False),
            }
        ), 400

    try:
        game_copy = update_game_copy_status_use_case.execute(copy_id, payload.action)
    except ValueError as exc:
        if str(exc) == "Game copy not found":
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 400
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(_serialize_game_copy(game_copy)), 200


@bp.route("/<int:copy_id>/location", methods=["PATCH"])
def update_game_copy_location(copy_id: int):
    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameCopyLocationUpdateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify(
            {
                "error": "Validation failed",
                "details": exc.errors(include_context=False),
            }
        ), 400

    try:
        game_copy = update_game_copy_location_use_case.execute(
            copy_id, payload.location
        )
    except ValueError as exc:
        if str(exc) == "Game copy not found":
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 400
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(_serialize_game_copy(game_copy)), 200


@bp.route("/<int:copy_id>/condition-note", methods=["PATCH"])
def update_game_copy_condition_note(copy_id: int):
    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameCopyConditionNoteUpdateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify(
            {
                "error": "Validation failed",
                "details": exc.errors(include_context=False),
            }
        ), 400

    try:
        game_copy = update_game_copy_condition_note_use_case.execute(
            copy_id, payload.condition_note
        )
    except ValueError as exc:
        if str(exc) == "Game copy not found":
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 400
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(_serialize_game_copy(game_copy)), 200