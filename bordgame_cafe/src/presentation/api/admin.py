"""Admin API endpoints for administrators."""

from flask import Blueprint, request, jsonify
from infrastructure.database import SessionLocal
from infrastructure.repositories import SQLAlchemyUserRepository

admin_bp = Blueprint("admin", __name__)


def get_user_repository():
    """Get user repository with session."""
    db = SessionLocal()
    return SQLAlchemyUserRepository(db)


@admin_bp.route("/users", methods=["GET"])
def list_users():
    """
    List all users.
    
    Query parameters:
    - skip: Number of users to skip (pagination)
    - limit: Maximum number of users to return
    """
    skip = request.args.get("skip", 0, type=int)
    limit = request.args.get("limit", 100, type=int)
    
    try:
        # TODO: Implement actual pagination
        return jsonify([]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get a specific user by ID."""
    try:
        user_repo = get_user_repository()
        user = user_repo.get_by_id(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(user.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete a user."""
    try:
        user_repo = get_user_repository()
        user = user_repo.get_by_id(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user_repo.delete(user_id)
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/users/<int:user_id>/activate", methods=["POST"])
def activate_user(user_id):
    """Activate a user account."""
    try:
        user_repo = get_user_repository()
        user = user_repo.get_by_id(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.is_active = True
        user_repo.update(user)
        
        return jsonify(user.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
def deactivate_user(user_id):
    """Deactivate a user account."""
    try:
        user_repo = get_user_repository()
        user = user_repo.get_by_id(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        user.is_active = False
        user_repo.update(user)
        
        return jsonify(user.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/reports/revenue", methods=["GET"])
def get_revenue_report():
    """Get revenue report for a date range."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        if not all([start_date, end_date]):
            return jsonify({"error": "Missing date range parameters"}), 400
        
        # TODO: Implement revenue report
        return jsonify({"error": "Not implemented"}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/reports/usage", methods=["GET"])
def get_usage_report():
    """Get usage statistics report."""
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        
        if not all([start_date, end_date]):
            return jsonify({"error": "Missing date range parameters"}), 400
        
        # TODO: Implement usage report
        return jsonify({"error": "Not implemented"}), 501
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@admin_bp.route("/system/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200
