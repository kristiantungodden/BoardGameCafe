from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import func

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.incident_db import IncidentDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.application.use_cases.user_use_cases import (
    CreateStewardCommand,
    ForcePasswordResetCommand,
    ListUsersQuery,
)
from features.users.composition.admin_use_case_factories import (
    get_create_steward_use_case,
    get_force_password_reset_use_case,
    get_list_users_use_case,
)
from features.users.composition.auth_use_case_factories import get_password_hasher
from features.users.domain.models.user import Role
from features.users.infrastructure.database.user_db import UserDB
from features.users.infrastructure.repositories import SqlAlchemyUserRepository
from features.users.presentation.schemas.admin_schema import StewardCreateRequest
from shared.domain.exceptions import ValidationError as DomainValidationError
from shared.infrastructure import db


bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _user_role_value(user) -> str | None:
    role = getattr(user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    if isinstance(role, str):
        return role
    return None


def _is_admin(user) -> bool:
    return _user_role_value(user) == "admin" or bool(getattr(user, "is_admin", False))


def _require_admin():
    if not getattr(current_user, "is_authenticated", False):
        return jsonify({"error": "Authentication required"}), 401
    if not _is_admin(current_user):
        return jsonify({"error": "Admin access required"}), 403
    return None


def _serialize_user(user) -> dict:
    role = getattr(user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "role": role,
        "force_password_change": bool(getattr(user, "force_password_change", False)),
    }


def _get_requesting_domain_user():
    return SqlAlchemyUserRepository().get_by_id(int(current_user.id))


def _count(model, *criteria) -> int:
    query = db.session.query(func.count(model.id))
    for criterion in criteria:
        query = query.filter(criterion)
    result = query.scalar()
    return int(result or 0)


@bp.get("/dashboard/stats")
def dashboard_stats():
    err = _require_admin()
    if err:
        return err

    user_rows = db.session.query(UserDB.role, func.count(UserDB.id)).group_by(UserDB.role).all()
    user_counts = {"customer": 0, "staff": 0, "admin": 0}
    for role, count in user_rows:
        user_counts[str(role)] = int(count or 0)

    game_copy_rows = db.session.query(GameCopyDB.status, func.count(GameCopyDB.id)).group_by(GameCopyDB.status).all()
    game_copy_counts = {"available": 0, "reserved": 0, "occupied": 0, "maintenance": 0, "lost": 0}
    for status, count in game_copy_rows:
        game_copy_counts[str(status)] = int(count or 0)

    table_rows = db.session.query(TableDB.status, func.count(TableDB.id)).group_by(TableDB.status).all()
    table_counts = {"available": 0, "occupied": 0, "reserved": 0, "maintenance": 0}
    for status, count in table_rows:
        table_counts[str(status)] = int(count or 0)

    booking_rows = db.session.query(BookingDB.status, func.count(BookingDB.id)).group_by(BookingDB.status).all()
    booking_counts = {"confirmed": 0, "seated": 0, "completed": 0, "cancelled": 0, "no_show": 0}
    for status, count in booking_rows:
        booking_counts[str(status)] = int(count or 0)

    payload = {
        "users_total": sum(user_counts.values()),
        "users_by_role": user_counts,
        "games_total": _count(GameDB),
        "copies_total": sum(game_copy_counts.values()),
        "copies_by_status": game_copy_counts,
        "tables_total": _count(TableDB),
        "tables_by_status": table_counts,
        "incidents_total": _count(IncidentDB),
        "bookings_total": sum(booking_counts.values()),
        "bookings_by_status": booking_counts,
        "open_bookings": booking_counts.get("confirmed", 0) + booking_counts.get("seated", 0),
        "open_incidents": _count(IncidentDB),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return jsonify(payload), 200


@bp.get("/users")
def list_users():
    err = _require_admin()
    if err:
        return err

    role_raw = (request.args.get("role") or "").strip().lower() or None
    search_text = (request.args.get("q") or "").strip() or None

    role = None
    if role_raw:
        if role_raw not in {"customer", "staff", "admin"}:
            return jsonify({"error": "Invalid role filter"}), 400
        role = Role(role_raw)

    requesting_user = _get_requesting_domain_user()
    if requesting_user is None:
        return jsonify({"error": "Authentication required"}), 401

    use_case = get_list_users_use_case()
    try:
        users = use_case.execute(ListUsersQuery(role=role, search_text=search_text), requesting_user)
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 403

    return jsonify([_serialize_user(user) for user in users]), 200


@bp.post("/stewards")
def create_steward():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        payload = StewardCreateRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 400

    requesting_user = _get_requesting_domain_user()
    if requesting_user is None:
        return jsonify({"error": "Authentication required"}), 401

    use_case = get_create_steward_use_case()
    hasher = get_password_hasher()
    try:
        steward = use_case.execute(
            CreateStewardCommand(
                name=payload.name,
                email=payload.email,
                password_hash=hasher.hash(payload.password),
                phone=payload.phone,
            ),
            requesting_user,
        )
    except DomainValidationError as exc:
        message = str(exc)
        status = 403 if message == "Admin access required" else 409
        return jsonify({"error": message}), status

    return jsonify(_serialize_user(steward)), 201


@bp.post("/users/<int:user_id>/force-password-reset")
def force_password_reset(user_id: int):
    err = _require_admin()
    if err:
        return err

    requesting_user = _get_requesting_domain_user()
    if requesting_user is None:
        return jsonify({"error": "Authentication required"}), 401

    use_case = get_force_password_reset_use_case()
    try:
        user = use_case.execute(ForcePasswordResetCommand(user_id=user_id), requesting_user)
    except DomainValidationError as exc:
        message = str(exc)
        if message == "User not found":
            return jsonify({"error": message}), 404
        return jsonify({"error": message}), 403

    return jsonify(_serialize_user(user)), 200