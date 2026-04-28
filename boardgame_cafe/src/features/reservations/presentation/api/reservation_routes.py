from datetime import datetime

from flask import Blueprint, current_app, redirect, flash, request, url_for
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError
from itsdangerous import BadSignature, SignatureExpired
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
    GetReservationByIdUseCase,
    ListReservationsUseCase,
    MarkReservationNoShowUseCase,
    SeatReservationUseCase,
)
from shared.application.services.reservation_transition_event_publisher import (
    publish_reservation_transition_event,
)
from shared.domain.datetime_utils import format_utc_iso, to_utc_aware, to_utc_naive
from shared.domain.exceptions import DomainError
from shared.domain.events import (
    ReservationCreated,
)
from features.payments.presentation.schemas.payment_schema import PaymentSchema
from features.reservations.presentation.schemas.reservation_schema import CreateReservationBookingRequest
from features.reservations.presentation.schemas.reservation_game_schema import AddReservationGameRequest
from features.reservations.composition.reservation_use_case_factories import (
    get_booking_availability_handler,
    get_booking_draft_use_case,
    get_create_booking_handler,
    get_add_game_to_reservation_use_case,
    get_cancel_reservation_use_case,
    get_complete_reservation_use_case,
    get_no_show_reservation_use_case,
    get_list_reservations_use_case,
    get_reservation_lookup_use_case,
    get_list_reservation_games_use_case,
    get_reservation_by_id_use_case,
    get_reservation_qr_use_case,
    get_reservation_status_history_use_case,
    get_remove_game_from_reservation_use_case,
    get_seat_reservation_use_case,
)

bp = Blueprint("reservations", __name__, url_prefix="/api/reservations")


def _is_staff_or_admin(user) -> bool:
    role = getattr(user, "role", None)
    if hasattr(role, "value"):
        role = role.value
    if role in {"staff", "admin"}:
        return True
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_admin", False))


def _can_view_reservation(user, reservation) -> bool:
    if _is_staff_or_admin(user):
        return True
    return getattr(reservation, "customer_id", None) == getattr(user, "id", None)


def _require_authenticated():
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401
    return None


def _require_staff_or_admin():
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401
    if not _is_staff_or_admin(current_user):
        return {"error": "Staff access required"}, 403
    return None


def _require_reservation_access(reservation):
    if _is_staff_or_admin(current_user):
        return None
    if getattr(reservation, "customer_id", None) != getattr(current_user, "id", None):
        return {"error": "Unauthorized access to reservation"}, 403
    return None


def _checkin_redirect_target(reservation_id: int) -> str:
    if "my_bookings_page" in current_app.view_functions:
        return url_for("my_bookings_page")
    return url_for("reservations.get_reservation", reservation_id=reservation_id)


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
        "start_ts": format_utc_iso(reservation.start_ts),
        "end_ts": format_utc_iso(reservation.end_ts),
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
        "created_at": format_utc_iso(entry.created_at),
    }


def _is_past_timestamp(ts: datetime) -> bool:
    return to_utc_aware(ts) < datetime.now(tz=to_utc_aware(ts).tzinfo)


@bp.get("")
def list_reservations():
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    use_case: ListReservationsUseCase = get_list_reservations_use_case()
    items = use_case.execute()
    
    # Filter to current user's reservations only (unless user is staff/admin)
    if not (hasattr(current_user, 'is_staff') and current_user.is_staff):
        items = [item for item in items if item.customer_id == current_user.id]
        items = [item for item in items if item.status != "created"]
    
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

    start_ts_utc = to_utc_naive(payload.start_ts)
    end_ts_utc = to_utc_naive(payload.end_ts)

    availability_handler = get_booking_availability_handler()
    result = availability_handler(start_ts_utc, end_ts_utc, payload.party_size)
    return result, 200


@bp.get("/<int:reservation_id>")
def get_reservation(reservation_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
    reservation = use_case.execute(reservation_id)
    if reservation is None:
        return {"error": "Reservation not found"}, 404
    
    auth_error = _require_reservation_access(reservation)
    if auth_error:
        return auth_error
    
    return _serialize_reservation(reservation), 200


@bp.get("/<int:reservation_id>/history")
def get_reservation_history(reservation_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    reservation_use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
    reservation = reservation_use_case.execute(reservation_id)
    if reservation is None:
        return {"error": "Reservation not found"}, 404

    auth_error = _require_reservation_access(reservation)
    if auth_error:
        return auth_error

    history_use_case = get_reservation_status_history_use_case()
    history = history_use_case.execute(reservation_id)
    return {
        "reservation_id": reservation_id,
        "history": [_serialize_status_history(item) for item in history],
    }, 200

@bp.post("")
def create_reservation():
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    try:
        raw = request.get_json()
    except BadRequest:
        return {"error": "Invalid JSON body"}, 400

    try:
        payload = CreateReservationBookingRequest.model_validate(raw or {})
    except PydanticValidationError as exc:
        return {"error": "Validation failed", "details": exc.errors()}, 400

    if _is_past_timestamp(payload.start_ts):
        return {"error": "Bookings cannot start in the past"}, 400

    start_ts_utc = to_utc_naive(payload.start_ts)
    end_ts_utc = to_utc_naive(payload.end_ts)

    create_booking = get_create_booking_handler()

    try:
        reservation, reservation_games, payment = create_booking(
            CreateReservationCommand(
                customer_id=current_user.id,
                **payload.model_dump(exclude={"games", "customer_id", "start_ts", "end_ts"}),
                start_ts=start_ts_utc,
                end_ts=end_ts_utc,
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
                table_numbers=response["table_ids"],
                start_ts=format_utc_iso(reservation.start_ts),
                end_ts=format_utc_iso(reservation.end_ts),
                party_size=reservation.party_size,
            )
        )
    get_reservation_qr_use_case().get_or_create_token(
        current_app.config["SECRET_KEY"],
        user_id=current_user.id,
        reservation_id=reservation.id,
    )
    return response, 201


def _run_status_transition(use_case, reservation_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    try:
        actor_role = getattr(current_user, "role", None)
        if hasattr(actor_role, "value"):
            actor_role = actor_role.value
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

    publish_reservation_transition_event(
        event_bus=getattr(current_app, "event_bus", None),
        reservation=reservation,
        actor_user_id=getattr(current_user, "id", None),
        actor_role=actor_role,
    )

    return _serialize_reservation(reservation), 200


@bp.patch("/<int:reservation_id>/cancel")
def cancel_reservation(reservation_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if not _is_staff_or_admin(current_user):
        reservation_use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
        reservation = reservation_use_case.execute(reservation_id)
        if reservation is None:
            return {"error": "Reservation not found"}, 404
        if getattr(reservation, "customer_id", None) != getattr(current_user, "id", None):
            return {"error": "Unauthorized access to reservation"}, 403

    use_case: CancelReservationUseCase = get_cancel_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch("/<int:reservation_id>/seat")
def seat_reservation(reservation_id: int):
    auth_error = _require_staff_or_admin()
    if auth_error:
        return auth_error

    use_case: SeatReservationUseCase = get_seat_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch("/<int:reservation_id>/complete")
def complete_reservation(reservation_id: int):
    auth_error = _require_staff_or_admin()
    if auth_error:
        return auth_error

    use_case: CompleteReservationUseCase = get_complete_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch("/<int:reservation_id>/no-show")
def no_show_reservation(reservation_id: int):
    auth_error = _require_staff_or_admin()
    if auth_error:
        return auth_error

    use_case: MarkReservationNoShowUseCase = get_no_show_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.post("/<int:reservation_id>/games")
def add_game_to_reservation(reservation_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if not _is_staff_or_admin(current_user):
        reservation_use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
        reservation = reservation_use_case.execute(reservation_id)
        if reservation is None:
            return {"error": "Reservation not found"}, 404
        auth_error = _require_reservation_access(reservation)
        if auth_error:
            return auth_error

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
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if not _is_staff_or_admin(current_user):
        reservation_use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
        reservation = reservation_use_case.execute(reservation_id)
        if reservation is None:
            return {"error": "Reservation not found"}, 404
        auth_error = _require_reservation_access(reservation)
        if auth_error:
            return auth_error

    use_case: ListReservationGamesUseCase = get_list_reservation_games_use_case()
    try:
        reservation_games = use_case.execute(reservation_id)
    except DomainError as exc:
        return {"error": str(exc)}, 404

    return [_serialize_reservation_game(item) for item in reservation_games], 200


@bp.delete("/<int:reservation_id>/games/<int:reservation_game_id>")
def remove_game_from_reservation(reservation_id: int, reservation_game_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    if not _is_staff_or_admin(current_user):
        reservation_use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
        reservation = reservation_use_case.execute(reservation_id)
        if reservation is None:
            return {"error": "Reservation not found"}, 404
        auth_error = _require_reservation_access(reservation)
        if auth_error:
            return auth_error

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


@bp.get("/<int:reservation_id>/qr")
def get_reservation_qr(reservation_id: int):
    auth_error = _require_authenticated()
    if auth_error:
        return auth_error

    reservation_use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
    reservation = reservation_use_case.execute(reservation_id)
    if reservation is None:
        return {"error": "Reservation not found"}, 404

    auth_error = _require_reservation_access(reservation)
    if auth_error:
        return auth_error

    qr_use_case = get_reservation_qr_use_case()
    token = qr_use_case.get_or_create_token(
        current_app.config["SECRET_KEY"],
        user_id=reservation.customer_id,
        reservation_id=reservation_id,
    )
    checkin_url = url_for("reservations.check_in_with_token", token=token, _external=True)
    svg = qr_use_case.generate_svg(checkin_url)
    response = current_app.response_class(svg, mimetype="image/svg+xml")
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/checkin/<string:token>")
def check_in_with_token(token: str):
    auth_error = _require_staff_or_admin()
    if auth_error:
        return auth_error

    try:
        qr_use_case = get_reservation_qr_use_case()
        reservation_id = qr_use_case.decode_token(current_app.config["SECRET_KEY"], token)
    except SignatureExpired:
        return {"error": "Reservation QR code expired"}, 400
    except BadSignature:
        return {"error": "Invalid reservation QR code"}, 400

    reservation_use_case: GetReservationByIdUseCase = get_reservation_by_id_use_case()
    reservation = reservation_use_case.execute(reservation_id)
    if reservation is None:
        return {"error": "Reservation not found"}, 404

    if reservation.status == "seated":
        flash(f"Reservation #{reservation_id} is already checked in.", "success")
        return redirect(_checkin_redirect_target(reservation_id))

    seat_use_case = get_seat_reservation_use_case()
    try:
        updated_reservation = seat_use_case.execute(reservation_id)
    except DomainError as exc:
        return {"error": str(exc)}, 400

    if updated_reservation is None:
        return {"error": "Reservation not found"}, 404

    flash(f"Reservation #{reservation_id} checked in successfully.", "success")
    return redirect(_checkin_redirect_target(reservation_id))

@bp.get("/draft")
def get_reservation_draft():
    """
    Get the current reservation draft from the server-side draft store.
    Returns the draft data or an empty object if no draft exists.
    """
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401

    draft = get_booking_draft_use_case().get(current_user.id)
    return draft, 200


@bp.post("/draft-save")
def save_reservation_draft():
    """
    Save or update the current reservation draft in the server-side draft store.
    The draft is stored temporarily and expires automatically.
    Supports partial updates by merging provided fields into existing draft data.
    """
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401

    try:
        raw = request.get_json()
    except BadRequest:
        return {"error": "Invalid JSON body"}, 400

    if raw is None:
        raw = {}

    # Empty payload means explicit clear request.
    draft_use_case = get_booking_draft_use_case()
    if raw == {}:
        draft_use_case.clear(current_user.id)
        return {"saved": True, "draft": {}}, 200

    # Accept partial payloads because the user may still be filling the form.
    try:
        existing_draft = draft_use_case.get(current_user.id)

        # Extract only supported fields present in this update payload.
        draft_update = {}
        if "party_size" in raw:
            draft_update["party_size"] = raw["party_size"]
        if "start_ts" in raw:
            draft_update["start_ts"] = raw["start_ts"]
        if "end_ts" in raw:
            draft_update["end_ts"] = raw["end_ts"]
        if "table_id" in raw:
            draft_update["table_id"] = raw["table_id"]
        if "table_ids" in raw:
            draft_update["table_ids"] = raw["table_ids"]
        if "notes" in raw:
            draft_update["notes"] = raw["notes"]
        if "games" in raw:
            draft_update["games"] = raw["games"]

        draft_data = {**existing_draft, **draft_update}

        draft_use_case.save(current_user.id, draft_data)

        return {"saved": True, "draft": draft_data}, 200
    except Exception as exc:
        return {"error": str(exc)}, 400
