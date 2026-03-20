"""Tables API endpoints."""

from flask import Blueprint, request, jsonify
from datetime import datetime
from infrastructure.database import SessionLocal
from infrastructure.repositories import SQLAlchemyTableRepository
from domain.models import Table

tables_bp = Blueprint("tables", __name__)


def get_table_repository():
    """Get table repository with session."""
    db = SessionLocal()
    return SQLAlchemyTableRepository(db)


@tables_bp.route("", methods=["GET"])
def list_tables():
    """
    List all tables.
    
    Query parameters:
    - skip: Number of tables to skip (pagination)
    - limit: Maximum number of tables to return
    """
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 100, type=int)
    
    try:
        # TODO: Implement actual pagination
        return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@tables_bp.route("/<int:table_id>", methods=["GET"])
def get_table(table_id):
    """Get a specific table by ID."""
    try:
        table_repo = get_table_repository()
        table = table_repo.get_by_id(table_id)
        
        if not table:
            return jsonify({"error": "Table not found"}), 404
        
        return jsonify(table.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@tables_bp.route("", methods=["POST"])
def create_table():
    """Create a new table."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        table = Table(**data)
        table_repo = get_table_repository()
        table_repo.add(table)
        
        return jsonify(table.dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@tables_bp.route("/<int:table_id>", methods=["PUT"])
def update_table(table_id):
    """Update an existing table."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is empty"}), 400
        
        table_repo = get_table_repository()
        table = table_repo.get_by_id(table_id)
        
        if not table:
            return jsonify({"error": "Table not found"}), 404
        
        # Update only provided fields
        for field, value in data.items():
            if value is not None:
                setattr(table, field, value)
        
        table_repo.update(table)
        return jsonify(table.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@tables_bp.route("/<int:table_id>", methods=["DELETE"])
def delete_table(table_id):
    """Delete a table."""
    try:
        table_repo = get_table_repository()
        table = table_repo.get_by_id(table_id)
        
        if not table:
            return jsonify({"error": "Table not found"}), 404
        
        table_repo.delete(table_id)
        return jsonify({"message": "Table deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@tables_bp.route("/available/search", methods=["GET"])
def get_available_tables():
    """Get tables available for a specific time slot and party size."""
    try:
        reserved_at = request.args.get("reserved_at")
        reserved_until = request.args.get("reserved_until")
        party_size = request.args.get("party_size", type=int)
        
        if not all([reserved_at, reserved_until, party_size]):
            return jsonify({"error": "Missing required parameters"}), 400
        
        # Parse datetime strings
        reserved_at = datetime.fromisoformat(reserved_at)
        reserved_until = datetime.fromisoformat(reserved_until)
        
        table_repo = get_table_repository()
        tables = table_repo.get_available_tables(reserved_at, reserved_until, party_size)
        
        return jsonify([t.dict() for t in tables]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
