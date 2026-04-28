from flask import Blueprint, current_app, request, jsonify, url_for
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest

from features.games.application.use_cases.game_copy_use_cases import (
    CreateGameCopyCommand,
)
from features.games.composition.game_use_case_factories import (
    get_game_copy_use_cases,
    get_game_copy_qr_use_case,
    rollback_games_transaction,
)
from features.games.domain.models.game_copy import GameCopy
from features.games.presentation.schemas.game_copy_schema import (
    GameCopyConditionNoteUpdateRequest,
    GameCopyCreateRequest,
    GameCopyLocationUpdateRequest,
    GameCopyStatusUpdateRequest,
)
from shared.domain.exceptions import DomainError

bp = Blueprint("game_copies", __name__, url_prefix="/api/game-copies")

copy_use_cases = get_game_copy_use_cases()


def _is_staff_or_admin(user) -> bool:
    role = getattr(user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    return role in {"staff", "admin"} or bool(
        getattr(user, "is_staff", False) or getattr(user, "is_admin", False)
    )


def _require_staff_or_admin():
    if not getattr(current_user, "is_authenticated", False):
        return jsonify({"error": "Authentication required"}), 401
    if not _is_staff_or_admin(current_user):
        return jsonify({"error": "Staff access required"}), 403
    return None


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


def _serialize_game_copy_db(game_copy_db) -> dict:
    return {
        "id": game_copy_db.id,
        "game_id": game_copy_db.game_id,
        "copy_code": game_copy_db.copy_code,
        "status": game_copy_db.status,
        "location": game_copy_db.location,
        "condition_note": game_copy_db.condition_note,
        "updated_at": game_copy_db.updated_at.isoformat()
        if hasattr(game_copy_db.updated_at, "isoformat")
        else game_copy_db.updated_at,
    }


@bp.route("/", methods=["GET"])
def list_game_copies():
    game_copies = copy_use_cases.list_all.execute()
    return jsonify([_serialize_game_copy(copy) for copy in game_copies]), 200


@bp.route("/<int:copy_id>", methods=["GET"])
def get_game_copy(copy_id: int):
    game_copy = copy_use_cases.get_by_id.execute(copy_id)
    if not game_copy:
        return jsonify({"error": "Game copy not found"}), 404

    return jsonify(_serialize_game_copy(game_copy)), 200


@bp.route("/", methods=["POST"])
def create_game_copy():
    err = _require_staff_or_admin()
    if err:
        return err

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
        game_copy = copy_use_cases.create.execute(
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
        rollback_games_transaction()
        return jsonify({"error": "copy_code already exists"}), 409

    return jsonify(_serialize_game_copy(game_copy)), 201


@bp.route("/<int:copy_id>/status", methods=["PATCH"])
def update_game_copy_status(copy_id: int):
    err = _require_staff_or_admin()
    if err:
        return err

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
        game_copy = copy_use_cases.update_status.execute(copy_id, payload.action)
    except ValueError as exc:
        if str(exc) == "Game copy not found":
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 400
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(_serialize_game_copy(game_copy)), 200


@bp.route("/<int:copy_id>/location", methods=["PATCH"])
def update_game_copy_location(copy_id: int):
    err = _require_staff_or_admin()
    if err:
        return err

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
        game_copy = copy_use_cases.update_location.execute(
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
    err = _require_staff_or_admin()
    if err:
        return err

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
        game_copy = copy_use_cases.update_condition_note.execute(
            copy_id, payload.condition_note
        )
    except ValueError as exc:
        if str(exc) == "Game copy not found":
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 400
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(_serialize_game_copy(game_copy)), 200


@bp.route("/<int:copy_id>/qr", methods=["GET"])
def get_game_copy_qr(copy_id: int):
    err = _require_staff_or_admin()
    if err:
        return err

    game_copy = copy_use_cases.get_by_id.execute(copy_id)
    if not game_copy:
        return jsonify({"error": "Game copy not found"}), 404

    qr_use_case = get_game_copy_qr_use_case()
    token = qr_use_case.get_or_create_token(copy_id)
    info_url = url_for("game_copies.get_game_copy_by_qr", token=token, _external=True)
    svg = qr_use_case.generate_svg(info_url)
    response = current_app.response_class(svg, mimetype="image/svg+xml")
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.route("/scan/<string:token>", methods=["GET"])
def get_game_copy_by_qr(token: str):
    err = _require_staff_or_admin()
    if err:
        return err

    copy_id = get_game_copy_qr_use_case().get_copy_id_by_token(token)
    if copy_id is None:
        return jsonify({"error": "Invalid game copy QR code"}), 404

    game_copy = copy_use_cases.get_by_id.execute(copy_id)
    if game_copy is None:
        return jsonify({"error": "Game copy not found"}), 404

    payload = _serialize_game_copy(game_copy)
    payload["qr_token"] = token
    return jsonify(payload), 200