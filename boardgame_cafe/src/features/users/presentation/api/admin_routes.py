from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from features.bookings.infrastructure.database.booking_db import BookingDB
from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.incident_db import IncidentDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.pricing_settings import (
    configure_base_fee,
    resolve_base_fee,
    set_cancel_time_limit_hours,
)
from features.users.infrastructure.database.announcement_db import AnnouncementDB
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
        "is_suspended": bool(getattr(user, "is_suspended", False)),
    }


def _serialize_game(row: GameDB) -> dict:
    return {
        "id": int(row.id),
        "title": row.title,
        "min_players": int(row.min_players),
        "max_players": int(row.max_players),
        "playtime_min": int(row.playtime_min),
        "price_cents": int(getattr(row, "price_cents", 0) or 0),
        "complexity": float(row.complexity),
        "description": row.description,
        "image_url": row.image_url,
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
    }


def _serialize_copy(row: GameCopyDB) -> dict:
    game = getattr(row, "game", None)
    return {
        "id": int(row.id),
        "game_id": int(row.game_id),
        "game_title": getattr(game, "title", None),
        "copy_code": row.copy_code,
        "status": row.status,
        "location": row.location,
        "condition_note": row.condition_note,
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
    }


def _serialize_incident(row: IncidentDB) -> dict:
    steward = getattr(row, "steward", None)
    game_copy = getattr(row, "game_copy", None)
    game = getattr(game_copy, "game", None) if game_copy is not None else None
    return {
        "id": int(row.id),
        "game_copy_id": int(row.game_copy_id),
        "game_copy_code": getattr(game_copy, "copy_code", None),
        "game_title": getattr(game, "title", None),
        "reported_by": int(row.reported_by),
        "reported_by_name": getattr(steward, "name", None),
        "incident_type": row.incident_type,
        "note": row.note,
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
    }


def _serialize_announcement(row: AnnouncementDB) -> dict:
    creator = getattr(row, "creator", None)
    return {
        "id": int(row.id),
        "title": row.title,
        "body": row.body,
        "cta_label": row.cta_label,
        "cta_url": row.cta_url,
        "is_published": bool(row.is_published),
        "published_at": row.published_at.isoformat() if getattr(row, "published_at", None) else None,
        "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
        "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
        "created_by": int(row.created_by) if row.created_by is not None else None,
        "created_by_name": getattr(creator, "name", None),
    }


def _parse_optional_text(value):
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _validate_announcement_cta(label: str | None, url: str | None) -> None:
    if bool(label) != bool(url):
        raise ValueError("cta_label and cta_url must either both be set or both be empty")

    if url and not (url.startswith("/") or url.startswith("http://") or url.startswith("https://")):
        raise ValueError("cta_url must start with /, http://, or https://")


def _get_requesting_domain_user():
    return SqlAlchemyUserRepository().get_by_id(int(current_user.id))


def _count(model, *criteria) -> int:
    query = db.session.query(func.count(model.id))
    for criterion in criteria:
        query = query.filter(criterion)
    result = query.scalar()
    return int(result or 0)


def _parse_non_negative_int(value, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer")
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return parsed


def _parse_optional_future_timestamp(value) -> int | None:
    if value in (None, ""):
        return None

    if not isinstance(value, str):
        raise ValueError("booking_base_fee_active_until must be an ISO datetime string")

    normalized = value.strip()
    if not normalized:
        return None

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("booking_base_fee_active_until must be a valid ISO datetime") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    if parsed <= now:
        raise ValueError("booking_base_fee_active_until must be in the future")

    return int(parsed.timestamp())


def _epoch_to_iso(value: int | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()


def _parse_non_negative_float(value, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a number")
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative")
    return parsed


def _parse_copy_status(value) -> str:
    allowed = {"available", "reserved", "in_use", "maintenance", "lost", "occupied"}
    status = str(value or "").strip().lower()
    if status not in allowed:
        raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
    return status


@bp.get("/catalogue")
def get_catalogue_overview():
    err = _require_admin()
    if err:
        return err

    query_text = (request.args.get("q") or "").strip().lower()

    games_query = db.session.query(GameDB).order_by(GameDB.title.asc())
    if query_text:
        games_query = games_query.filter(GameDB.title.ilike(f"%{query_text}%"))
    games = games_query.all()

    copies_query = db.session.query(GameCopyDB).join(GameDB, GameDB.id == GameCopyDB.game_id).order_by(GameCopyDB.copy_code.asc())
    if query_text:
        copies_query = copies_query.filter(
            db.or_(
                GameCopyDB.copy_code.ilike(f"%{query_text}%"),
                GameDB.title.ilike(f"%{query_text}%"),
                GameCopyDB.location.ilike(f"%{query_text}%"),
            )
        )
    copies = copies_query.all()

    return jsonify(
        {
            "games": [_serialize_game(game) for game in games],
            "copies": [_serialize_copy(copy_row) for copy_row in copies],
        }
    ), 200


@bp.post("/catalogue/games")
def create_catalogue_game():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        title = str(raw.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")

        min_players = _parse_non_negative_int(raw.get("min_players"), "min_players")
        max_players = _parse_non_negative_int(raw.get("max_players"), "max_players")
        playtime_min = _parse_non_negative_int(raw.get("playtime_min"), "playtime_min")
        if min_players < 1 or max_players < 1:
            raise ValueError("min_players and max_players must be at least 1")
        if min_players > max_players:
            raise ValueError("min_players cannot exceed max_players")

        complexity = _parse_non_negative_float(raw.get("complexity"), "complexity")
        if complexity > 5:
            raise ValueError("complexity must be between 0 and 5")

        price_cents = _parse_non_negative_int(raw.get("price_cents", 0), "price_cents")
        description = raw.get("description")
        image_url = raw.get("image_url")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    row = GameDB(
        title=title,
        min_players=min_players,
        max_players=max_players,
        playtime_min=playtime_min,
        price_cents=price_cents,
        complexity=complexity,
        description=description,
        image_url=image_url,
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(_serialize_game(row)), 201


@bp.put("/catalogue/games/<int:game_id>")
def update_catalogue_game(game_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(GameDB, game_id)
    if row is None:
        return jsonify({"error": "Game not found"}), 404

    raw = request.get_json(silent=True) or {}
    if not raw:
        return jsonify({"error": "At least one field must be provided"}), 400

    try:
        if "title" in raw:
            title = str(raw.get("title") or "").strip()
            if not title:
                raise ValueError("title cannot be blank")
            row.title = title

        if "min_players" in raw:
            row.min_players = _parse_non_negative_int(raw.get("min_players"), "min_players")
        if "max_players" in raw:
            row.max_players = _parse_non_negative_int(raw.get("max_players"), "max_players")
        if row.min_players < 1 or row.max_players < 1:
            raise ValueError("min_players and max_players must be at least 1")
        if row.min_players > row.max_players:
            raise ValueError("min_players cannot exceed max_players")

        if "playtime_min" in raw:
            row.playtime_min = _parse_non_negative_int(raw.get("playtime_min"), "playtime_min")
        if "price_cents" in raw:
            row.price_cents = _parse_non_negative_int(raw.get("price_cents"), "price_cents")
        if "complexity" in raw:
            complexity = _parse_non_negative_float(raw.get("complexity"), "complexity")
            if complexity > 5:
                raise ValueError("complexity must be between 0 and 5")
            row.complexity = complexity
        if "description" in raw:
            row.description = raw.get("description")
        if "image_url" in raw:
            row.image_url = raw.get("image_url")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    db.session.commit()
    return jsonify(_serialize_game(row)), 200


@bp.delete("/catalogue/games/<int:game_id>")
def delete_catalogue_game(game_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(GameDB, game_id)
    if row is None:
        return jsonify({"error": "Game not found"}), 404

    copy_count = _count(GameCopyDB, GameCopyDB.game_id == game_id)
    if copy_count > 0:
        return jsonify({"error": "Delete copies for this game before deleting the game."}), 409

    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "Game deleted"}), 200


@bp.post("/catalogue/copies")
def create_catalogue_copy():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        game_id = int(raw.get("game_id"))
        copy_code = str(raw.get("copy_code") or "").strip()
        if not copy_code:
            raise ValueError("copy_code is required")
        status = _parse_copy_status(raw.get("status") or "available")
        location = raw.get("location")
        condition_note = raw.get("condition_note")
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400

    if db.session.get(GameDB, game_id) is None:
        return jsonify({"error": "Game not found"}), 404

    row = GameCopyDB(
        game_id=game_id,
        copy_code=copy_code,
        status=status,
        location=location,
        condition_note=condition_note,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "copy_code already exists"}), 409

    return jsonify(_serialize_copy(row)), 201


@bp.put("/catalogue/copies/<int:copy_id>")
def update_catalogue_copy(copy_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(GameCopyDB, copy_id)
    if row is None:
        return jsonify({"error": "Game copy not found"}), 404

    raw = request.get_json(silent=True) or {}
    if not raw:
        return jsonify({"error": "At least one field must be provided"}), 400

    try:
        if "copy_code" in raw:
            copy_code = str(raw.get("copy_code") or "").strip()
            if not copy_code:
                raise ValueError("copy_code cannot be blank")
            row.copy_code = copy_code
        if "status" in raw:
            next_status = _parse_copy_status(raw.get("status"))
            if row.status != "available" and next_status == "available":
                has_open_incidents = (
                    db.session.query(IncidentDB.id)
                    .filter(IncidentDB.game_copy_id == copy_id)
                    .first()
                    is not None
                )
                if has_open_incidents:
                    return jsonify({"error": "Resolve incidents before setting copy to available."}), 409
            row.status = next_status
        if "location" in raw:
            row.location = raw.get("location")
        if "condition_note" in raw:
            row.condition_note = raw.get("condition_note")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "copy_code already exists"}), 409

    return jsonify(_serialize_copy(row)), 200


@bp.delete("/catalogue/copies/<int:copy_id>")
def delete_catalogue_copy(copy_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(GameCopyDB, copy_id)
    if row is None:
        return jsonify({"error": "Game copy not found"}), 404

    # Delete dependent incidents first to avoid FK/NOT NULL constraint failure
    db.session.query(IncidentDB).filter(IncidentDB.game_copy_id == copy_id).delete()

    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "Game copy deleted"}), 200


@bp.get("/catalogue/copies/<int:copy_id>/incidents")
def list_catalogue_copy_incidents(copy_id: int):
    err = _require_admin()
    if err:
        return err

    if db.session.get(GameCopyDB, copy_id) is None:
        return jsonify({"error": "Game copy not found"}), 404

    rows = (
        db.session.query(IncidentDB)
        .filter(IncidentDB.game_copy_id == copy_id)
        .order_by(IncidentDB.created_at.desc(), IncidentDB.id.desc())
        .all()
    )
    return jsonify([_serialize_incident(row) for row in rows]), 200


@bp.get("/catalogue/incidents")
def list_catalogue_incidents():
    err = _require_admin()
    if err:
        return err

    rows = (
        db.session.query(IncidentDB)
        .order_by(IncidentDB.created_at.desc(), IncidentDB.id.desc())
        .all()
    )
    return jsonify([_serialize_incident(row) for row in rows]), 200


@bp.post("/catalogue/incidents/<int:incident_id>/resolve")
def resolve_catalogue_incident(incident_id: int):
    err = _require_admin()
    if err:
        return err

    incident = db.session.get(IncidentDB, incident_id)
    if incident is None:
        return jsonify({"error": "Incident not found"}), 404

    copy_row = db.session.get(GameCopyDB, int(incident.game_copy_id))
    if copy_row is None:
        return jsonify({"error": "Game copy not found"}), 404

    # Resolving an incident means restoring the copy to normal availability.
    copy_row.status = "available"
    db.session.delete(incident)
    db.session.commit()

    return jsonify({"message": "Incident resolved", "copy": _serialize_copy(copy_row)}), 200


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
        "published_announcements": int(db.session.query(func.count(AnnouncementDB.id)).filter(AnnouncementDB.is_published.is_(True)).scalar() or 0),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return jsonify(payload), 200


@bp.get("/content/announcements")
def list_announcements():
    err = _require_admin()
    if err:
        return err

    rows = (
        db.session.query(AnnouncementDB)
        .order_by(AnnouncementDB.created_at.desc(), AnnouncementDB.id.desc())
        .all()
    )
    return jsonify([_serialize_announcement(row) for row in rows]), 200


@bp.post("/content/announcements")
def create_announcement():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        title = str(raw.get("title") or "").strip()
        body = str(raw.get("body") or "").strip()
        if not title:
            raise ValueError("title is required")
        if not body:
            raise ValueError("body is required")

        cta_label = _parse_optional_text(raw.get("cta_label"))
        cta_url = _parse_optional_text(raw.get("cta_url"))
        _validate_announcement_cta(cta_label, cta_url)

        publish_now = bool(raw.get("publish_now", False))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        creator_id = int(getattr(current_user, "id", 0) or 0)
    except (TypeError, ValueError):
        creator_id = None

    row = AnnouncementDB(
        title=title,
        body=body,
        cta_label=cta_label,
        cta_url=cta_url,
        is_published=publish_now,
        published_at=datetime.now(timezone.utc) if publish_now else None,
        created_by=creator_id,
    )
    db.session.add(row)
    db.session.commit()

    return jsonify(_serialize_announcement(row)), 201


@bp.put("/content/announcements/<int:announcement_id>")
def update_announcement(announcement_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(AnnouncementDB, announcement_id)
    if row is None:
        return jsonify({"error": "Announcement not found"}), 404

    raw = request.get_json(silent=True) or {}
    if not raw:
        return jsonify({"error": "At least one field must be provided"}), 400

    try:
        if "title" in raw:
            title = str(raw.get("title") or "").strip()
            if not title:
                raise ValueError("title cannot be blank")
            row.title = title

        if "body" in raw:
            body = str(raw.get("body") or "").strip()
            if not body:
                raise ValueError("body cannot be blank")
            row.body = body

        if "cta_label" in raw:
            row.cta_label = _parse_optional_text(raw.get("cta_label"))
        if "cta_url" in raw:
            row.cta_url = _parse_optional_text(raw.get("cta_url"))

        _validate_announcement_cta(row.cta_label, row.cta_url)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    db.session.commit()
    return jsonify(_serialize_announcement(row)), 200


@bp.post("/content/announcements/<int:announcement_id>/publish")
def publish_announcement(announcement_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(AnnouncementDB, announcement_id)
    if row is None:
        return jsonify({"error": "Announcement not found"}), 404

    row.is_published = True
    row.published_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(_serialize_announcement(row)), 200


@bp.post("/content/announcements/<int:announcement_id>/unpublish")
def unpublish_announcement(announcement_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(AnnouncementDB, announcement_id)
    if row is None:
        return jsonify({"error": "Announcement not found"}), 404

    row.is_published = False
    db.session.commit()
    return jsonify(_serialize_announcement(row)), 200


@bp.delete("/content/announcements/<int:announcement_id>")
def delete_announcement(announcement_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(AnnouncementDB, announcement_id)
    if row is None:
        return jsonify({"error": "Announcement not found"}), 404

    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "Announcement deleted"}), 200


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


@bp.patch("/users/<int:user_id>/suspension")
def set_user_suspension(user_id: int):
    err = _require_admin()
    if err:
        return err

    target = db.session.get(UserDB, user_id)
    if target is None:
        return jsonify({"error": "User not found"}), 404

    try:
        current_user_id = int(getattr(current_user, "id", 0) or 0)
    except (TypeError, ValueError):
        current_user_id = 0

    if target.id == current_user_id:
        return jsonify({"error": "You cannot suspend your own account."}), 400

    raw = request.get_json(silent=True) or {}
    suspend_value = raw.get("suspended")
    if not isinstance(suspend_value, bool):
        return jsonify({"error": "suspended must be true or false"}), 400

    if _user_role_value(target) == "admin" and suspend_value:
        active_admin_count = _count(UserDB, UserDB.role == "admin", UserDB.is_suspended.is_(False))
        if active_admin_count <= 1:
            return jsonify({"error": "Cannot suspend the last active admin account."}), 409

    target.is_suspended = suspend_value
    db.session.commit()

    return jsonify(_serialize_user(target)), 200


@bp.get("/pricing")
def get_pricing():
    err = _require_admin()
    if err:
        return err

    fee_state = resolve_base_fee(
        db.session,
        cleanup_expired=True,
    )
    if fee_state["changed"]:
        db.session.commit()

    table_rows = db.session.query(TableDB).order_by(TableDB.floor.asc(), TableDB.table_nr.asc()).all()
    game_rows = db.session.query(GameDB).order_by(GameDB.title.asc()).all()

    payload = {
        "booking_base_fee_cents": int(fee_state["effective_fee_cents"]),
        "booking_base_fee_priority": int(fee_state["effective_priority"]),
        "booking_base_fee_default_cents": int(fee_state["base_fee_cents"]),
        "booking_base_fee_default_priority": int(fee_state["base_priority"]),
        "booking_base_fee_override_cents": fee_state["override_fee_cents"],
        "booking_base_fee_override_priority": int(fee_state["override_priority"]),
        "booking_base_fee_active_until": _epoch_to_iso(fee_state["active_until_epoch"]),
        "booking_base_fee_has_temporary_override": bool(fee_state["override_is_active"]),
        "booking_cancel_time_limit_hours": int(fee_state["booking_cancel_time_limit_hours"]),
        "tables": [
            {
                "id": row.id,
                "table_nr": row.table_nr,
                "floor": row.floor,
                "zone": row.zone,
                "capacity": row.capacity,
                "price_cents": int(getattr(row, "price_cents", 0) or 0),
            }
            for row in table_rows
        ],
        "games": [
            {
                "id": row.id,
                "title": row.title,
                "price_cents": int(getattr(row, "price_cents", 0) or 0),
            }
            for row in game_rows
        ],
    }
    return jsonify(payload), 200


@bp.put("/pricing/base-fee")
def update_base_fee():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        value = _parse_non_negative_int(raw.get("booking_base_fee_cents"), "booking_base_fee_cents")
        priority = _parse_non_negative_int(raw.get("booking_base_fee_priority", 0), "booking_base_fee_priority")
        cancel_limit_hours = _parse_non_negative_int(
            raw.get("booking_cancel_time_limit_hours", 24),
            "booking_cancel_time_limit_hours",
        )
        active_until_epoch = _parse_optional_future_timestamp(
            raw.get("booking_base_fee_active_until")
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    configure_base_fee(
        db.session,
        value,
        active_until_epoch=active_until_epoch,
        priority=priority,
    )
    set_cancel_time_limit_hours(db.session, cancel_limit_hours)
    db.session.commit()
    fee_state = resolve_base_fee(db.session)
    return jsonify(
        {
            "booking_base_fee_cents": int(fee_state["effective_fee_cents"]),
            "booking_base_fee_priority": int(fee_state["effective_priority"]),
            "booking_base_fee_default_cents": int(fee_state["base_fee_cents"]),
            "booking_base_fee_default_priority": int(fee_state["base_priority"]),
            "booking_base_fee_override_cents": fee_state["override_fee_cents"],
            "booking_base_fee_override_priority": int(fee_state["override_priority"]),
            "booking_base_fee_active_until": _epoch_to_iso(fee_state["active_until_epoch"]),
            "booking_base_fee_has_temporary_override": bool(fee_state["override_is_active"]),
            "booking_cancel_time_limit_hours": int(fee_state["booking_cancel_time_limit_hours"]),
        }
    ), 200


@bp.put("/pricing/tables/<int:table_id>")
def update_table_price(table_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(TableDB, table_id)
    if row is None:
        return jsonify({"error": "Table not found"}), 404

    raw = request.get_json(silent=True) or {}
    try:
        value = _parse_non_negative_int(raw.get("price_cents"), "price_cents")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    row.price_cents = value
    db.session.commit()
    return jsonify({"id": row.id, "price_cents": int(row.price_cents)}), 200


@bp.put("/pricing/games/<int:game_id>")
def update_game_price(game_id: int):
    err = _require_admin()
    if err:
        return err

    row = db.session.get(GameDB, game_id)
    if row is None:
        return jsonify({"error": "Game not found"}), 404

    raw = request.get_json(silent=True) or {}
    try:
        value = _parse_non_negative_int(raw.get("price_cents"), "price_cents")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    row.price_cents = value
    db.session.commit()
    return jsonify({"id": row.id, "price_cents": int(row.price_cents)}), 200