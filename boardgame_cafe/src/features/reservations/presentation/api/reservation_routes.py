from flask import Blueprint, current_app, request
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError
from werkzeug.exceptions import BadRequest

from features.reservations.application.use_cases.reservation_game_use_cases import (
    AddGameToReservationCommand,
    AddGameToReservationUseCase,
    ListReservationGamesUseCase,
    RemoveGameFromReservationUseCase,
)
from features.reservations.application.use_cases.reservation_lookup_use_cases import (
    GetReservationLookupUseCase,
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
from shared.domain.events import ReservationCreated
from shared.infrastructure import csrf
from features.payments.presentation.schemas.payment_schema import PaymentSchema
from features.reservations.presentation.schemas.reservation_schema import CreateReservationRequest
from features.reservations.presentation.schemas.reservation_schema import CreateReservationBookingRequest
from features.reservations.presentation.schemas.reservation_game_schema import AddReservationGameRequest
from features.reservations.presentation.api.deps import (
    get_booking_availability_handler,
    get_create_booking_handler,
    get_add_game_to_reservation_use_case,
    get_cancel_reservation_use_case,
    get_complete_reservation_use_case,
    get_create_reservation_use_case,
    get_no_show_reservation_use_case,
    get_list_reservations_use_case,
    get_reservation_lookup_use_case,
    get_list_reservation_games_use_case,
    get_reservation_by_id_use_case,
    get_reservation_status_history_use_case,
    get_remove_game_from_reservation_use_case,
    get_seat_reservation_use_case,
)

bp = Blueprint("reservations", __name__, url_prefix="/api/reservations")


def _serialize_reservation(reservation):
    table_id = getattr(reservation, "table_id", None)
    table_ids = getattr(reservation, "table_ids", None)
    if table_ids is None:
        table_ids = [table_id] if table_id is not None else []

    return {
        "id": reservation.id,
        "customer_id": reservation.customer_id,
        "table_id": table_id,
        "table_ids": table_ids,
        "start_ts": reservation.start_ts.isoformat(),
        "end_ts": reservation.end_ts.isoformat(),
        "party_size": reservation.party_size,
        "status": reservation.status,
        "notes": reservation.notes,
    }


def _serialize_reservation_game(reservation_game):
    return {
        "id": reservation_game.id,
        "booking_id": reservation_game.booking_id,
        "requested_game_id": reservation_game.requested_game_id,
        "game_copy_id": reservation_game.game_copy_id,
    }


def _serialize_status_history(entry):
    return {
        "id": entry.id,
        "booking_id": entry.booking_id,
        "from_status": entry.from_status,
        "to_status": entry.to_status,
        "source": entry.source,
        "reason": entry.reason,
        "actor_user_id": entry.actor_user_id,
        "actor_role": entry.actor_role,
        "created_at": entry.created_at.isoformat(),
    }


@bp.get("")
def list_reservations():
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401

    use_case: ListReservationsUseCase = get_list_reservations_use_case()
    items = use_case.execute()
    
    # Filter to current user's reservations only (unless user is staff/admin)
    if not (hasattr(current_user, 'is_staff') and current_user.is_staff):
        items = [item for item in items if item.customer_id == current_user.id]
    
    return [_serialize_reservation(item) for item in items], 200


@bp.get("/lookup")
def get_reservation_lookup_data():
    use_case: GetReservationLookupUseCase = get_reservation_lookup_use_case()
    return use_case.execute(), 200


@bp.get("/availability")
def get_booking_availability():
    try:
        start_ts = request.args["start_ts"]
        end_ts = request.args["end_ts"]
        party_size = int(request.args["party_size"])
    except (KeyError, ValueError):
        return {"error": "start_ts, end_ts and party_size are required"}, 400

    try:
        payload = CreateReservationBookingRequest.model_validate(
            {
                "party_size": party_size,
                "start_ts": start_ts,
                "end_ts": end_ts,
            }
        )
    except PydanticValidationError as exc:
        return {"error": "Validation failed", "details": exc.errors()}, 400

    availability_handler = get_booking_availability_handler()
    result = availability_handler(payload.start_ts, payload.end_ts, payload.party_size)
    return result, 200


@bp.get("/<int:reservation_id>")
def get_reservation(reservation_id: int):
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401

    use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
    reservation = use_case.execute(reservation_id)
    if reservation is None:
        return {"error": "Reservation not found"}, 404
    
    # Check authorization: user can only view their own reservation (unless staff)
    if not (hasattr(current_user, 'is_staff') and current_user.is_staff):
        if reservation.customer_id != current_user.id:
            return {"error": "Unauthorized access to reservation"}, 403
    
    return _serialize_reservation(reservation), 200


@bp.get("/<int:reservation_id>/history")
def get_reservation_history(reservation_id: int):
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401

    reservation_use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
    reservation = reservation_use_case.execute(reservation_id)
    if reservation is None:
        return {"error": "Reservation not found"}, 404

    if not (hasattr(current_user, "is_staff") and current_user.is_staff):
        if reservation.customer_id != current_user.id:
            return {"error": "Unauthorized access to reservation"}, 403

    history_use_case = get_reservation_status_history_use_case()
    history = history_use_case.execute(reservation_id)
    return {
        "reservation_id": reservation_id,
        "history": [_serialize_status_history(item) for item in history],
    }, 200

@bp.post("")
def create_reservation():
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401

    try:
        raw = request.get_json()
    except BadRequest:
        return {"error": "Invalid JSON body"}, 400

    try:
        payload = CreateReservationBookingRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return {"error": "Validation failed", "details": exc.errors()}, 400

    create_booking = get_create_booking_handler()

    try:
        reservation, reservation_games, payment = create_booking(
            CreateReservationCommand(
                customer_id=current_user.id,
                **payload.model_dump(exclude={"games", "customer_id"}),
            ),
            games=[item.model_dump() for item in payload.games],
        )
    except (DomainError, ValueError) as exc:
        return {"error": str(exc)}, 400

    response = _serialize_reservation(reservation)
    response["games"] = [_serialize_reservation_game(item) for item in reservation_games]
    response["payment"] = PaymentSchema.dump(payment)

    event_bus = getattr(current_app, "event_bus", None)
    if event_bus is not None:
        event_bus.publish(
            ReservationCreated(
                reservation_id=reservation.id,
                user_id=current_user.id,
                user_email=getattr(current_user, "email", None),
                reservation_details=(
                    f"Reservation #{reservation.id}: "
                    f"{reservation.start_ts.isoformat()} to {reservation.end_ts.isoformat()}, "
                    f"party_size={reservation.party_size}, tables={response['table_ids']}"
                ),
            )
        )
    return response, 201


def _run_status_transition(use_case, reservation_id: int):
    try:
        actor_role = getattr(current_user, "role", None)
        if actor_role is None and getattr(current_user, "is_staff", False):
            actor_role = "staff"
        if actor_role is None and getattr(current_user, "is_authenticated", False):
            actor_role = "customer"

        reservation = use_case.execute(
            reservation_id,
            actor_user_id=getattr(current_user, "id", None),
            actor_role=actor_role,
        )
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


@bp.get("/<int:reservation_id>/games")
def list_games_for_reservation(reservation_id: int):
    use_case: ListReservationGamesUseCase = get_list_reservation_games_use_case()
    try:
        reservation_games = use_case.execute(reservation_id)
    except DomainError as exc:
        return {"error": str(exc)}, 404

    return [_serialize_reservation_game(item) for item in reservation_games], 200


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

