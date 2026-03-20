"""Steward API endpoints for staff."""

from flask import Blueprint, request, jsonify
from infrastructure.database import SessionLocal
from infrastructure.repositories import SQLAlchemyGameRepository

steward_bp = Blueprint("steward", __name__)


def get_game_repository():
    """Get game repository with session."""
    db = SessionLocal()
    return SQLAlchemyGameRepository(db)


@steward_bp.route("/game-copies", methods=["GET"])
def list_game_copies():
    """
    List all game copies.
    
    Query parameters:
    - skip: Number of copies to skip (pagination)
    - limit: Maximum number of copies to return
    """
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 100, type=int)
    
    try:
        # TODO: Implement pagination from GameCopyRepository
        return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@steward_bp.route("/game-copies/<int:copy_id>", methods=["GET"])
def get_game_copy(copy_id):
    """Get a specific game copy by ID."""
    try:
        # TODO: Implement when GameCopyRepository is ready
        return jsonify({"error": "Not implemented"}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@steward_bp.route("/game-copies/<int:copy_id>", methods=["PUT"])
def update_game_copy(copy_id):
    """Update a game copy."""
    try:
        # TODO: Implement when GameCopyRepository is ready
        return jsonify({"error": "Not implemented"}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@steward_bp.route("/game-copies/<int:copy_id>/assign", methods=["POST"])
def assign_game_to_reservation(copy_id):
    """Assign a game copy to a reservation."""
    try:
        data = request.get_json()
        reservation_id = data.get("reservation_id")
        
        # Get current steward id (TODO: from JWT token)
        steward_id = 1  # Placeholder
        
        # TODO: Implement
        return jsonify({"error": "Not implemented"}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@steward_bp.route("/game-copies/<int:copy_id>/checkout", methods=["POST"])
def checkout_game(copy_id):
    """Check out a game copy."""
    try:
        data = request.get_json()
        reservation_id = data.get("reservation_id")
        
        # Get current steward id (TODO: from JWT token)
        steward_id = 1  # Placeholder
        
        # TODO: Implement
        return jsonify({"error": "Not implemented"}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@steward_bp.route("/game-copies/<int:copy_id>/return", methods=["POST"])
def return_game(copy_id):
    """Return a game copy."""
    try:
        data = request.get_json()
        reservation_id = data.get("reservation_id")
        
        # Get current steward id (TODO: from JWT token)
        steward_id = 1  # Placeholder
        
        # TODO: Implement
        return jsonify({"error": "Not implemented"}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@steward_bp.route("/game-copies/<int:copy_id>/report-damage", methods=["POST"])
def report_damage(copy_id):
    """Report damage on a game copy."""
    try:
        data = request.get_json()
        severity = data.get("severity")
        description = data.get("description")
        
        # Get current steward id (TODO: from JWT token)
        steward_id = 1  # Placeholder
        
        # TODO: Implement
        return jsonify({"error": "Not implemented"}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 400
