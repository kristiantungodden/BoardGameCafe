from __future__ import annotations

import json

from flask import Blueprint, jsonify, request
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError

from features.tables.application.use_cases.admin_table_use_cases import (
    CreateZoneCommand,
    CreateFloorCommand,
    CreateTableCommand,
    UpdateFloorCommand,
    UpdateTableCommand,
    UpdateZoneCommand,
)
from features.tables.composition.admin_use_case_factories import (
    get_create_zone_use_case,
    get_create_floor_use_case,
    get_create_table_use_case,
    get_delete_floor_use_case,
    get_delete_table_use_case,
    get_delete_zone_use_case,
    get_force_delete_floor_use_case,
    get_force_delete_table_use_case,
    get_force_delete_zone_use_case,
    get_list_floors_use_case,
    get_list_tables_use_case,
    get_list_zones_use_case,
    get_update_floor_use_case,
    get_update_table_use_case,
    get_update_zone_use_case,
)
from features.tables.presentation.schemas.admin_schema import FloorRequest, TableRequest, ZoneRequest
from shared.domain.exceptions import ValidationError as DomainValidationError


bp = Blueprint("admin_tables", __name__, url_prefix="/api/admin")


def _require_admin():
    if not getattr(current_user, "is_authenticated", False):
        return jsonify({"error": "Authentication required"}), 401
    role = getattr(current_user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    if role != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return None


def _serialize_floor(floor):
    return {
        "id": floor.id,
        "number": floor.number,
        "name": floor.name,
        "active": floor.active,
        "notes": floor.notes,
    }


def _serialize_table(table):
    return {
        "id": table.id,
        "number": table.number,
        "capacity": table.capacity,
        "floor": table.floor,
        "zone": table.zone,
        "features": table.features or {},
        "width": table.width,
        "height": table.height,
        "rotation": table.rotation,
        "status": table.status,
    }


def _serialize_zone(zone):
    return {
        "id": zone.id,
        "floor": zone.floor,
        "name": zone.name,
        "active": zone.active,
        "notes": zone.notes,
    }


def _is_force_delete() -> bool:
    raw = (request.args.get("force") or "").strip().lower()
    return raw in {"1", "true", "yes", "y"}


@bp.get("/floors")
def list_floors():
    err = _require_admin()
    if err:
        return err
    floors = get_list_floors_use_case().execute()
    return jsonify([_serialize_floor(floor) for floor in floors]), 200


@bp.post("/floors")
def create_floor():
    err = _require_admin()
    if err:
        return err
    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        payload = FloorRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": json.loads(exc.json())}), 400
    try:
        floor = get_create_floor_use_case().execute(CreateFloorCommand(**payload.model_dump()))
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_serialize_floor(floor)), 201


@bp.patch("/floors/<int:floor_id>")
def update_floor(floor_id: int):
    err = _require_admin()
    if err:
        return err
    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        payload = FloorRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": json.loads(exc.json())}), 400
    try:
        floor = get_update_floor_use_case().execute(UpdateFloorCommand(floor_id=floor_id, **payload.model_dump()))
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_serialize_floor(floor)), 200


@bp.delete("/floors/<int:floor_id>")
def delete_floor(floor_id: int):
    err = _require_admin()
    if err:
        return err
    try:
        if not _is_force_delete():
            get_delete_floor_use_case().execute(floor_id)
            return "", 204

        get_force_delete_floor_use_case().execute(floor_id)
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return "", 204


@bp.get("/zones")
def list_zones():
    err = _require_admin()
    if err:
        return err
    floor = request.args.get("floor", type=int)
    zones = get_list_zones_use_case().execute(floor=floor)
    return jsonify([_serialize_zone(zone) for zone in zones]), 200


@bp.post("/zones")
def create_zone():
    err = _require_admin()
    if err:
        return err
    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        payload = ZoneRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": json.loads(exc.json())}), 400
    try:
        zone = get_create_zone_use_case().execute(CreateZoneCommand(**payload.model_dump()))
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_serialize_zone(zone)), 201


@bp.patch("/zones/<int:zone_id>")
def update_zone(zone_id: int):
    err = _require_admin()
    if err:
        return err
    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        payload = ZoneRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": json.loads(exc.json())}), 400
    try:
        zone = get_update_zone_use_case().execute(UpdateZoneCommand(zone_id=zone_id, **payload.model_dump()))
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_serialize_zone(zone)), 200


@bp.delete("/zones/<int:zone_id>")
def delete_zone(zone_id: int):
    err = _require_admin()
    if err:
        return err
    try:
        if not _is_force_delete():
            get_delete_zone_use_case().execute(zone_id)
            return "", 204

        get_force_delete_zone_use_case().execute(zone_id)
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return "", 204


@bp.get("/tables")
def list_tables():
    err = _require_admin()
    if err:
        return err
    floor = request.args.get("floor", type=int)
    tables = get_list_tables_use_case().execute(floor=floor)
    return jsonify([_serialize_table(table) for table in tables]), 200


@bp.post("/tables")
def create_table():
    err = _require_admin()
    if err:
        return err
    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        payload = TableRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": json.loads(exc.json())}), 400
    try:
        table = get_create_table_use_case().execute(CreateTableCommand(**payload.model_dump()))
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_serialize_table(table)), 201


@bp.patch("/tables/<int:table_id>")
def update_table(table_id: int):
    err = _require_admin()
    if err:
        return err
    raw = request.get_json(silent=True)
    if raw is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    try:
        payload = TableRequest.model_validate(raw)
    except PydanticValidationError as exc:
        return jsonify({"error": "Validation failed", "details": json.loads(exc.json())}), 400
    try:
        table = get_update_table_use_case().execute(UpdateTableCommand(table_id=table_id, **payload.model_dump()))
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(_serialize_table(table)), 200


@bp.delete("/tables/<int:table_id>")
def delete_table(table_id: int):
    err = _require_admin()
    if err:
        return err
    try:
        if _is_force_delete():
            get_force_delete_table_use_case().execute(table_id)
        else:
            get_delete_table_use_case().execute(table_id)
    except DomainValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return "", 204