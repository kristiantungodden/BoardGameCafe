from decimal import Decimal

from flask import Blueprint, request, jsonify
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError
from werkzeug.exceptions import BadRequest

from features.games.application.use_cases.game_use_cases import GameUseCases
from features.games.application.use_cases.game_tag_use_cases import (
    AttachGameTagCommand,
    CreateGameTagCommand,
)
from features.games.composition.game_use_case_factories import (
    get_game_tag_use_cases,
    get_game_use_cases,
    get_games_filtered,
)
from features.games.domain.models.game import Game
from features.games.domain.models.game_tag import GameTag
from features.games.domain.models.game_tag_link import GameTagLink
from features.games.presentation.schemas.game_schema import (
    GameCreateRequest,
    GameTagCreateRequest,
    GameTagLinkCreateRequest,
    GameUpdateRequest,
)
from shared.domain.exceptions import DomainError

bp = Blueprint("games", __name__, url_prefix="/api/games")

use_cases: GameUseCases = get_game_use_cases()
tag_use_cases = get_game_tag_use_cases()


def _require_admin():
    if not getattr(current_user, "is_authenticated", False):
        return jsonify({"error": "Authentication required"}), 401
    if getattr(current_user, "role", None) != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return None


def _serialize_game(game: Game) -> dict:
    tags = [_serialize_tag(tag) for tag in (game.tags or [])]
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
        "tags": tags,
    }


def _serialize_tag(tag: GameTag) -> dict:
    return {
        "id": tag.id,
        "name": tag.name,
    }


def _serialize_tag_link(link: GameTagLink) -> dict:
    return {
        "id": link.id,
        "game_id": link.game_id,
        "game_tag_id": link.game_tag_id,
    }


@bp.route("/", methods=["GET"])
def get_games():
    # Get query parameters for filtering and pagination
    page_param = request.args.get("page", None)
    page_size_param = request.args.get("page_size", None)
    search = request.args.get("search", None, type=str)
    min_players = request.args.get("min_players", None, type=int)
    max_players = request.args.get("max_players", None, type=int)
    complexity = request.args.get("complexity", None, type=float)
    tag_name = request.args.get("tag", None, type=str)
    tags_param = request.args.get("tags", None, type=str)
    if not tag_name and tags_param:
        tag_name = tags_param
    
    # Parse page and page_size with defaults
    page = int(page_param) if page_param else 1
    page_size = int(page_size_param) if page_size_param else 10
    
    # Check if any filter or explicit pagination params are provided
    has_filters = any([page_param, page_size_param, search, min_players is not None, max_players is not None, complexity is not None, tag_name])
    
    if has_filters:
        # Use filtered and paginated results
        try:
            games, total_count, page, page_size = get_games_filtered(
                page=page,
                page_size=page_size,
                search=search,
                min_players=min_players,
                max_players=max_players,
                complexity=complexity,
                tag_name=tag_name,
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 400
        
        serialized_games = [_serialize_game(game) for game in games]
        
        total_pages = (total_count + page_size - 1) // page_size
        response = {
            "games": serialized_games,
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
        }
        return jsonify(response), 200
    else:
        # Default behavior: return plain list for backward compatibility
        games = use_cases.get_all_games()
        serialized_games = [_serialize_game(game) for game in games]
        return jsonify(serialized_games), 200


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

    try:
        use_cases.delete_game(game_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify({"message": "Game deleted"}), 200


@bp.route("/tags", methods=["POST"])
def create_tag():
    err = _require_admin()
    if err:
        return err

    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameTagCreateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors(include_context=False)}), 400

    try:
        tag = tag_use_cases.create.execute(CreateGameTagCommand(name=payload.name))
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(_serialize_tag(tag)), 201


@bp.route("/tags", methods=["GET"])
def list_tags():
    tags = tag_use_cases.list_all.execute()
    return jsonify([_serialize_tag(tag) for tag in tags]), 200


@bp.route("/<int:game_id>/tags", methods=["POST"])
def attach_tag_to_game(game_id: int):
    err = _require_admin()
    if err:
        return err

    try:
        raw = request.get_json()
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = GameTagLinkCreateRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors(include_context=False)}), 400

    try:
        link = tag_use_cases.attach.execute(
            AttachGameTagCommand(game_id=game_id, tag_id=payload.tag_id)
        )
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(_serialize_tag_link(link)), 201


@bp.route("/<int:game_id>/tags", methods=["GET"])
def list_tags_for_game(game_id: int):
    try:
        tags = tag_use_cases.list_for_game.execute(game_id)
    except DomainError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify([_serialize_tag(tag) for tag in tags]), 200


@bp.route("/<int:game_id>/tags/<int:tag_id>", methods=["DELETE"])
def remove_tag_from_game(game_id: int, tag_id: int):
    err = _require_admin()
    if err:
        return err

    removed = tag_use_cases.remove.execute(game_id, tag_id)
    if not removed:
        return jsonify({"error": "Game tag link not found"}), 404

    return {}, 204