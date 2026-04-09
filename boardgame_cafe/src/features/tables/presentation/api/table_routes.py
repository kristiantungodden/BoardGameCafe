from __future__ import annotations

import json

from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError

from features.tables.presentation.schemas.table_availability_schema import (
    TableAvailabilityQuery,
)
from features.tables.presentation.api.deps import get_table_availability_use_case


bp = Blueprint("tables", __name__, url_prefix="/api/tables")


@bp.get("/availability")
def get_table_availability():
    try:
        payload = TableAvailabilityQuery.model_validate(request.args.to_dict())
    except PydanticValidationError as exc:
        return {"error": "Validation failed", "details": json.loads(exc.json())}, 400

    use_case = get_table_availability_use_case()
    result = use_case.execute(
        payload.start_ts,
        payload.end_ts,
        payload.party_size,
        payload.floor,
    )
    return result, 200