from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError
from werkzeug.exceptions import BadRequest

from features.reservations.application.use_cases.reservation_use_cases import (
    CreateReservationCommand,
    CreateReservationUseCase,
    GetReservationByIdUseCase,
    ListReservationsUseCase,
)
from shared.domain.exceptions import DomainError
from shared.infrastructure import csrf
from features.reservations.presentation.schemas.reservation_schema import CreateReservationRequest
from shared.presentation.api.deps import (
    get_create_reservation_use_case,
    get_list_reservations_use_case,
    get_reservation_by_id_use_case,
)

bp = Blueprint("reservations", __name__, url_prefix="/api/reservations")


def _serialize_reservation(reservation):
    return {
        "id": reservation.id,
        "customer_id": reservation.customer_id,
        "table_id": reservation.table_id,
        "start_ts": reservation.start_ts.isoformat(),
        "end_ts": reservation.end_ts.isoformat(),
        "party_size": reservation.party_size,
        "status": reservation.status,
        "notes": reservation.notes,
    }


@bp.get("")
def list_reservations():
    use_case: ListReservationsUseCase = get_list_reservations_use_case()
    items = use_case.execute()
    return [_serialize_reservation(item) for item in items], 200


@bp.get("/<int:reservation_id>")
def get_reservation(reservation_id: int):
    use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
    reservation = use_case.execute(reservation_id)
    if reservation is None:
        return {"error": "Reservation not found"}, 404
    return _serialize_reservation(reservation), 200

@bp.post("")
def create_reservation():
    try:
        raw = request.get_json()
    except BadRequest:
        return {"error": "Invalid JSON body"}, 400

    try:
        payload = CreateReservationRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return {"error": "Validation failed", "details": exc.errors()}, 400

    use_case: CreateReservationUseCase = get_create_reservation_use_case()

    try:
        reservation = use_case.execute(
            CreateReservationCommand(**payload.model_dump())
        )
    except DomainError as exc:
        return {"error": str(exc)}, 400

    return _serialize_reservation(reservation), 201