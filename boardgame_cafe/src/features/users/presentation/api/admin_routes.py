from __future__ import annotations

from flask import Blueprint, Response, jsonify, request
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError

from features.users.application.use_cases.admin_catalogue_use_cases import ConflictError
from features.users.application.use_cases.admin_pricing_use_cases import (
    UpdateBaseFeeCommand,
    UpdatePriceCommand,
)
from features.users.application.use_cases.admin_user_admin_use_cases import (
    StewardPayload,
    SuspensionPolicyConflictError,
    SuspensionPolicyViolationError,
    UserAdminAccessDeniedError,
    UserAdminConflictError,
    UserAdminNotFoundError,
)
from features.users.composition.admin_use_case_factories import (
    get_catalogue_management_use_case,
    get_content_management_use_case,
    get_incident_resolution_use_case,
    get_pricing_management_use_case,
    get_reports_query_service,
    get_reports_use_case,
    get_user_admin_actions_use_case,
)
from features.users.composition.auth_use_case_factories import get_password_hasher
from features.users.presentation.schemas.admin_schema import (
    AnnouncementCreateRequest,
    AnnouncementUpdateRequest,
    PricingBaseFeeUpdateRequest,
    PricingItemUpdateRequest,
    StewardCreateRequest,
    SuspensionUpdateRequest,
)
from shared.domain.exceptions import ValidationError as DomainValidationError


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


def _current_user_id() -> int | None:
    try:
        return int(getattr(current_user, "id", 0) or 0)
    except (TypeError, ValueError):
        return None


@bp.get("/catalogue")
def get_catalogue_overview():
    err = _require_admin()
    if err:
        return err

    query_text = request.args.get("q")
    payload = get_catalogue_management_use_case().get_overview(query_text)
    return jsonify(payload), 200


@bp.post("/catalogue/games")
def create_catalogue_game():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        payload = get_catalogue_management_use_case().create_game(raw)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(payload), 201


@bp.put("/catalogue/games/<int:game_id>")
def update_catalogue_game(game_id: int):
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        payload = get_catalogue_management_use_case().update_game(game_id, raw)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(payload), 200


@bp.delete("/catalogue/games/<int:game_id>")
def delete_catalogue_game(game_id: int):
    err = _require_admin()
    if err:
        return err

    try:
        get_catalogue_management_use_case().delete_game(game_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ConflictError as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify({"message": "Game deleted"}), 200


@bp.post("/catalogue/copies")
def create_catalogue_copy():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        payload = get_catalogue_management_use_case().create_copy(raw)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except ConflictError as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify(payload), 201


@bp.put("/catalogue/copies/<int:copy_id>")
def update_catalogue_copy(copy_id: int):
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True) or {}
    try:
        payload = get_catalogue_management_use_case().update_copy(copy_id, raw)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except ConflictError as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify(payload), 200


@bp.delete("/catalogue/copies/<int:copy_id>")
def delete_catalogue_copy(copy_id: int):
    err = _require_admin()
    if err:
        return err

    try:
        get_catalogue_management_use_case().delete_copy(copy_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify({"message": "Game copy deleted"}), 200


@bp.get("/catalogue/copies/<int:copy_id>/incidents")
def list_catalogue_copy_incidents(copy_id: int):
    err = _require_admin()
    if err:
        return err

    try:
        payload = get_incident_resolution_use_case().list_copy_incidents(copy_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(payload), 200


@bp.get("/catalogue/incidents")
def list_catalogue_incidents():
    err = _require_admin()
    if err:
        return err

    payload = get_incident_resolution_use_case().list_incidents()
    return jsonify(payload), 200


@bp.post("/catalogue/incidents/<int:incident_id>/resolve")
def resolve_catalogue_incident(incident_id: int):
    err = _require_admin()
    if err:
        return err

    try:
        payload = get_incident_resolution_use_case().resolve_incident(incident_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(payload), 200


@bp.get("/dashboard/stats")
def dashboard_stats():
    err = _require_admin()
    if err:
        return err

    payload = get_reports_use_case().dashboard_stats()
    return jsonify(payload), 200


@bp.get("/content/announcements")
def list_announcements():
    err = _require_admin()
    if err:
        return err

    payload = get_content_management_use_case().list_announcements()
    return jsonify(payload), 200


@bp.post("/content/announcements")
def create_announcement():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        req = AnnouncementCreateRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 400

    creator_id = _current_user_id()
    try:
        payload = get_content_management_use_case().create_announcement(req.model_dump(), creator_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(payload), 201


@bp.put("/content/announcements/<int:announcement_id>")
def update_announcement(announcement_id: int):
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        req = AnnouncementUpdateRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 400

    try:
        payload = get_content_management_use_case().update_announcement(
            announcement_id,
            req.model_dump(exclude_unset=True),
        )
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(payload), 200


@bp.post("/content/announcements/<int:announcement_id>/publish")
def publish_announcement(announcement_id: int):
    err = _require_admin()
    if err:
        return err

    try:
        payload = get_content_management_use_case().publish_announcement(announcement_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify(payload), 200


@bp.post("/content/announcements/<int:announcement_id>/unpublish")
def unpublish_announcement(announcement_id: int):
    err = _require_admin()
    if err:
        return err

    try:
        payload = get_content_management_use_case().unpublish_announcement(announcement_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 409
    return jsonify(payload), 200


@bp.delete("/content/announcements/<int:announcement_id>")
def delete_announcement(announcement_id: int):
    err = _require_admin()
    if err:
        return err

    try:
        get_content_management_use_case().delete_announcement(announcement_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404

    return jsonify({"message": "Announcement deleted"}), 200


@bp.get("/users")
def list_users():
    err = _require_admin()
    if err:
        return err

    role_raw = (request.args.get("role") or "").strip().lower() or None
    search_text = (request.args.get("q") or "").strip() or None
    requesting_user_id = _current_user_id()
    if requesting_user_id is None:
        return jsonify({"error": "Authentication required"}), 401

    try:
        payload = get_user_admin_actions_use_case().list_users(role_raw, search_text, requesting_user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 403

    return jsonify(payload), 200


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

    requesting_user_id = _current_user_id()
    if requesting_user_id is None:
        return jsonify({"error": "Authentication required"}), 401

    hasher = get_password_hasher()
    try:
        created = get_user_admin_actions_use_case().create_steward(
            StewardPayload(
                name=payload.name,
                email=payload.email,
                password=payload.password,
                phone=payload.phone,
            ),
            requesting_user_id,
            password_hash=hasher.hash(payload.password),
        )
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    except UserAdminAccessDeniedError as exc:
        return jsonify({"error": str(exc)}), 403
    except UserAdminConflictError as exc:
        return jsonify({"error": str(exc)}), 409
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(created), 201


@bp.post("/users/<int:user_id>/force-password-reset")
def force_password_reset(user_id: int):
    err = _require_admin()
    if err:
        return err

    requesting_user_id = _current_user_id()
    if requesting_user_id is None:
        return jsonify({"error": "Authentication required"}), 401

    try:
        payload = get_user_admin_actions_use_case().force_password_reset(user_id, requesting_user_id)
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    except UserAdminNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except UserAdminAccessDeniedError as exc:
        return jsonify({"error": str(exc)}), 403
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(payload), 200


@bp.patch("/users/<int:user_id>/suspension")
def set_user_suspension(user_id: int):
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        req = SuspensionUpdateRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 400

    acting_user_id = _current_user_id()
    if acting_user_id is None:
        return jsonify({"error": "Authentication required"}), 401

    try:
        payload = get_user_admin_actions_use_case().set_suspension(user_id, req.suspended, acting_user_id)
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except SuspensionPolicyConflictError as exc:
        return jsonify({"error": str(exc)}), 409
    except (SuspensionPolicyViolationError, DomainValidationError) as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(payload), 200


@bp.get("/pricing")
def get_pricing():
    err = _require_admin()
    if err:
        return err

    payload = get_pricing_management_use_case().get_pricing()
    return jsonify(payload), 200


@bp.put("/pricing/base-fee")
def update_base_fee():
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        req = PricingBaseFeeUpdateRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 400

    try:
        payload = get_pricing_management_use_case().update_base_fee(
            UpdateBaseFeeCommand(
                booking_base_fee_cents=req.booking_base_fee_cents,
                booking_base_fee_priority=req.booking_base_fee_priority,
                booking_cancel_time_limit_hours=req.booking_cancel_time_limit_hours,
                booking_base_fee_active_until=req.booking_base_fee_active_until,
            )
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(payload), 200


@bp.put("/pricing/tables/<int:table_id>")
def update_table_price(table_id: int):
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        req = PricingItemUpdateRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 400

    try:
        payload = get_pricing_management_use_case().update_table_price(
            table_id,
            UpdatePriceCommand(price_cents=req.price_cents),
        )
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(payload), 200


@bp.put("/pricing/games/<int:game_id>")
def update_game_price(game_id: int):
    err = _require_admin()
    if err:
        return err

    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        req = PricingItemUpdateRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.errors()}), 400

    try:
        payload = get_pricing_management_use_case().update_game_price(
            game_id,
            UpdatePriceCommand(price_cents=req.price_cents),
        )
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(payload), 200


@bp.get("/reports/registrations")
def reports_registrations():
    err = _require_admin()
    if err:
        return err

    query_service = get_reports_query_service()
    days = query_service.normalize_days(request.args.get("days"))
    return jsonify(query_service.registrations_report(days)), 200


@bp.get("/reports/revenue")
def reports_revenue():
    err = _require_admin()
    if err:
        return err

    query_service = get_reports_query_service()
    days = query_service.normalize_days(request.args.get("days"))
    return jsonify(query_service.revenue_report(days)), 200


@bp.get("/reports/top-games")
def reports_top_games():
    err = _require_admin()
    if err:
        return err

    query_service = get_reports_query_service()
    days = query_service.normalize_days(request.args.get("days"))
    return jsonify(query_service.top_games_report(days)), 200


@bp.get("/reports/revenue/csv")
def reports_revenue_csv():
    err = _require_admin()
    if err:
        return err

    query_service = get_reports_query_service()
    days = query_service.normalize_days(request.args.get("days"))
    csv_body, filename = query_service.revenue_csv(days)
    return Response(
        csv_body,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
