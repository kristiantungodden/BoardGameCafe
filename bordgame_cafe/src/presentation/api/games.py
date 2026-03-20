"""Games API endpoints."""

from flask import Blueprint, request, jsonify
from infrastructure.database import SessionLocal
from infrastructure.repositories import SQLAlchemyGameRepository
from domain.models import Game

games_bp = Blueprint("games", __name__)


def get_game_repository():
    """Get game repository with session."""
    db = SessionLocal()
    return SQLAlchemyGameRepository(db)


@games_bp.route("", methods=["GET"])
def list_games():
    """
    List all games.
    
    Query parameters:
    - skip: Number of games to skip (pagination)
    - limit: Maximum number of games to return
    """
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 100, type=int)
    
    try:
        # TODO: Implement actual pagination
        return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@games_bp.route("/<int:game_id>", methods=["GET"])
def get_game(game_id):
    """Get a specific game by ID."""
    try:
        game_repo = get_game_repository()
        game = game_repo.get_by_id(game_id)
        
        if not game:
            return jsonify({"error": "Game not found"}), 404
        
        return jsonify(game.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@games_bp.route("", methods=["POST"])
def create_game():
    """Create a new game."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        game = Game(**data)
        game_repo = get_game_repository()
        game_repo.add(game)
        
        return jsonify(game.dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@games_bp.route("/<int:game_id>", methods=["PUT"])
def update_game(game_id):
    """Update an existing game."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        game_repo = get_game_repository()
        game = game_repo.get_by_id(game_id)
        
        if not game:
            return jsonify({"error": "Game not found"}), 404
        
        # Update only provided fields
        for field, value in data.items():
            if value is not None:
                setattr(game, field, value)
        
        game_repo.update(game)
        return jsonify(game.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@games_bp.route("/<int:game_id>", methods=["DELETE"])
def delete_game(game_id):
    """Delete a game."""
    try:
        game_repo = get_game_repository()
        game = game_repo.get_by_id(game_id)
        
        if not game:
            return jsonify({"error": "Game not found"}), 404
        
        game_repo.delete(game_id)
        return jsonify({"message": "Game deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@games_bp.route("/search/title", methods=["GET"])
def search_games_by_title():
    """Search games by title."""
    title = request.args.get("title", "", type=str)
    
    if not title:
        return jsonify({"error": "Title parameter required"}), 400
    
    try:
        game_repo = get_game_repository()
        games = game_repo.search_by_title(title)
        return jsonify([g.dict() for g in games]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@games_bp.route("/search/tags", methods=["GET"])
def search_games_by_tags():
    """Search games by tags."""
    tags = request.args.getlist("tags")
    
    if not tags:
        return jsonify({"error": "At least one tag required"}), 400
    
    try:
        game_repo = get_game_repository()
        games = game_repo.get_by_tags(tags)
        return jsonify([g.dict() for g in games]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
