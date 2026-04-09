"""Steward/Admin routes for user management."""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from werkzeug.exceptions import BadRequest
from pydantic import ValidationError as PydanticValidationError

from shared.domain.exceptions import ValidationError as DomainValidationError
from features.users.presentation.api.deps import (
    get_create_user_use_case,
    get_update_user_use_case,
    get_change_password_use_case,
    get_get_user_use_case,
    get_list_users_use_case,
    get_delete_user_use_case,
)
from features.users.presentation.schemas.user_schema import UserCreate, UserUpdate, UserResponse
from features.users.application.use_cases.user_use_cases import (
    CreateUserCommand,
    UpdateUserCommand,
    ChangePasswordCommand,
)
from features.users.infrastructure import hash_password

bp = Blueprint("steward", __name__, url_prefix="/api/steward")


def _is_json_request() -> bool:
    return request.is_json


@bp.route("/users", methods=["GET"])
@login_required
def list_users():
    """List all users (admin/staff only)."""
    try:
        use_case = get_list_users_use_case()
        users = use_case.execute(current_user)
        return jsonify([UserResponse.from_domain(u).model_dump() for u in users]), 200
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 403


@bp.route("/users/<int:user_id>", methods=["GET"])
@login_required
def get_user(user_id: int):
    """Get a specific user (admin/staff only)."""
    try:
        use_case = get_get_user_use_case()
        user = use_case.execute(user_id, current_user)
        return jsonify(UserResponse.from_domain(user).model_dump()), 200
    except DomainValidationError as exc:
        if "not found" in str(exc).lower():
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 403


@bp.route("/users", methods=["POST"])
@login_required
def create_user():
    """Create a new user (admin only)."""
    try:
        raw = request.get_json() or {}
        payload = UserCreate.model_validate(raw)
    except (BadRequest, PydanticValidationError) as exc:
        return jsonify({"error": "Validation failed", "details": str(exc)}), 400

    try:
        # Hash password if provided
        password_hash = hash_password(payload.password) if payload.password else None
        cmd = CreateUserCommand(
            name=payload.name,
            email=payload.email,
            password_hash=password_hash,
            role=payload.role or "customer",
            phone=payload.phone,
        )
        use_case = get_create_user_use_case()
        user = use_case.execute(cmd)
        return jsonify(UserResponse.from_domain(user).model_dump()), 201
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/users/<int:user_id>", methods=["PUT"])
@login_required
def update_user(user_id: int):
    """Update a user (admin/
    )."""
    try:
        raw = request.get_json() or {}
        payload = UserUpdate.model_validate(raw)
    except (BadRequest, PydanticValidationError) as exc:
        return jsonify({"error": "Validation failed", "details": str(exc)}), 400

    try:
        cmd = UpdateUserCommand(
            user_id=user_id,
            name=payload.name,
            phone=payload.phone,
            role=payload.role,
        )
        use_case = get_update_user_use_case()
        user = use_case.execute(cmd, current_user)
        return jsonify(UserResponse.from_domain(user).model_dump()), 200
    except DomainValidationError as exc:
        if "not found" in str(exc).lower():
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 403


@bp.route("/users/<int:user_id>/change-password", methods=["POST"])
@login_required
def change_password(user_id: int):
    """Force password change for a user (admin only)."""
    try:
        raw = request.get_json() or {}
        new_password = raw.get("new_password")
        if not new_password or len(new_password.strip()) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
    except BadRequest:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        password_hash = hash_password(new_password)
        cmd = ChangePasswordCommand(
            user_id=user_id,
            new_password_hash=password_hash,
        )
        use_case = get_change_password_use_case()
        user = use_case.execute(cmd, current_user)
        return jsonify(UserResponse.from_domain(user).model_dump()), 200
    except DomainValidationError as exc:
        if "not found" in str(exc).lower():
            return jsonify({"error": str(exc)}), 404
        return jsonify({"error": str(exc)}), 403


@bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id: int):
    """Delete a user (admin only)."""
    try:
        use_case = get_delete_user_use_case()
        success = use_case.execute(user_id, current_user)
        if success:
            return jsonify({"message": "User deleted successfully"}), 204
        return jsonify({"error": "User not found"}), 404
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 403
