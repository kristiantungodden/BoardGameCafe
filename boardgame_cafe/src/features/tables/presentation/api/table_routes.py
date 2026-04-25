from __future__ import annotations

import json

from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError

from features.tables.presentation.schemas.table_availability_schema import (
    TableAvailabilityQuery,
)
from features.tables.composition.table_use_case_factories import get_table_availability_use_case
from shared.domain.datetime_utils import to_utc_naive


bp = Blueprint("tables", __name__, url_prefix="/api/tables")


@bp.get("/availability")
def get_table_availability():
    try:
        payload = TableAvailabilityQuery.model_validate(request.args.to_dict())
    except PydanticValidationError as exc:
        return {"error": "Validation failed", "details": json.loads(exc.json())}, 400

    use_case = get_table_availability_use_case()
    result = use_case.execute(
        to_utc_naive(payload.start_ts),
        to_utc_naive(payload.end_ts),
        payload.party_size,
        payload.floor,
    )
    return result, 200