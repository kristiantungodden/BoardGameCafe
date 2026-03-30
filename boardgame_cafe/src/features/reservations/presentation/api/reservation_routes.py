from flask import Blueprint, request
from pydantic import ValidationError as PydanticValidationError
from werkzeug.exceptions import BadRequest

from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationCommand,
    AddGameToReservationUseCase,
    RemoveGameFromReservationUseCase,
)
from features.reservations.application.use_cases.reservation_use_cases import (
    CancelReservationUseCase,
    CompleteReservationUseCase,
    CreateReservationCommand,
    CreateReservationUseCase,
    GetReservationByIdUseCase,
    ListReservationsUseCase,
    MarkReservationNoShowUseCase,
    SeatReservationUseCase,
)
from shared.domain.exceptions import DomainError
from shared.infrastructure import csrf
from features.reservations.presentation.schemas.reservation_schema import CreateReservationRequest
from features.reservations.presentation.schemas.reservation_game_schema import AddReservationGameRequest
from shared.presentation.api.deps import (
    get_add_game_to_reservation_use_case,
    get_cancel_reservation_use_case,
    get_complete_reservation_use_case,
    get_create_reservation_use_case,
    get_no_show_reservation_use_case,
    get_list_reservations_use_case,
    get_reservation_by_id_use_case,
    get_remove_game_from_reservation_use_case,
    get_seat_reservation_use_case,
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


def _serialize_reservation_game(reservation_game):
    return {
        "id": reservation_game.id,
        "table_reservation_id": reservation_game.table_reservation_id,
        "requested_game_id": reservation_game.requested_game_id,
        "game_copy_id": reservation_game.game_copy_id,
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


def _run_status_transition(use_case, reservation_id: int):
    try:
        reservation = use_case.execute(reservation_id)
    except DomainError as exc:
        return {"error": str(exc)}, 400

    if reservation is None:
        return {"error": "Reservation not found"}, 404

    return _serialize_reservation(reservation), 200


@bp.patch("/<int:reservation_id>/cancel")
def cancel_reservation(reservation_id: int):
    use_case: CancelReservationUseCase = get_cancel_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch("/<int:reservation_id>/seat")
def seat_reservation(reservation_id: int):
    use_case: SeatReservationUseCase = get_seat_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch("/<int:reservation_id>/complete")
def complete_reservation(reservation_id: int):
    use_case: CompleteReservationUseCase = get_complete_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch("/<int:reservation_id>/no-show")
def no_show_reservation(reservation_id: int):
    use_case: MarkReservationNoShowUseCase = get_no_show_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.post("/<int:reservation_id>/games")
def add_game_to_reservation(reservation_id: int):
    try:
        raw = request.get_json()
    except BadRequest:
        return {"error": "Invalid JSON body"}, 400

    try:
        payload = AddReservationGameRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return {"error": "Validation failed", "details": exc.errors()}, 400

    use_case: AddGameToReservationUseCase = get_add_game_to_reservation_use_case()

    try:
        reservation_game = use_case.execute(
            AddGameToReservationCommand(
                reservation_id=reservation_id,
                **payload.model_dump(),
            )
        )
    except DomainError as exc:
        return {"error": str(exc)}, 400

    return _serialize_reservation_game(reservation_game), 201


@bp.delete("/<int:reservation_id>/games/<int:reservation_game_id>")
def remove_game_from_reservation(reservation_id: int, reservation_game_id: int):
    use_case: RemoveGameFromReservationUseCase = (
        get_remove_game_from_reservation_use_case()
    )

    try:
        removed = use_case.execute(reservation_id, reservation_game_id)
    except DomainError as exc:
        return {"error": str(exc)}, 400

    if not removed:
        return {"error": "Reservation game not found"}, 404

    return {}, 204

