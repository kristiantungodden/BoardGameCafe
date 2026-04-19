from flask import Blueprint, current_app, request
from flask_login import current_user, login_required

from features.reservations.application.use_cases.reservation_game_use_cases import SwapGameCopyUseCase
from features.reservations.application.use_cases.reservation_use_cases import (
    ListActiveReservationsUseCase,
    ListConfirmedReservationsUseCase,
    ListSeatedReservationsUseCase,
)
from features.reservations.application.use_cases.steward_reservation_browse_use_cases import (
    BrowseStewardReservationsQuery,
    BrowseStewardReservationsUseCase,
)
from features.bookings.application.use_cases.booking_lifecycle_use_cases import (
    CompleteBookingUseCase,
    MarkBookingNoShowUseCase,
    SeatBookingUseCase,
)
from features.games.application.use_cases.game_copy_use_cases import (
    ListGameCopiesUseCase,
    UpdateGameCopyStatusUseCase,
)
from features.games.application.use_cases.game_copy_browse_use_cases import (
    BrowseGameCopiesQuery,
    BrowseGameCopiesUseCase,
)
from features.games.application.use_cases.incident_use_cases import (
    ListIncidentsForGameCopyUseCase,
    ListIncidentsUseCase,
    ReportIncidentUseCase,
)
from features.reservations.application.use_cases.waitlist_use_cases import (
    ListWaitlistUseCase,
    AddToWaitlistUseCase,
    RemoveFromWaitlistUseCase,
)
from shared.application.services.reservation_transition_event_publisher import (
    publish_reservation_transition_event,
)
from shared.domain.exceptions import DomainError
from features.users.presentation.api.deps.get_steward_use_cases import (
    get_complete_reservation_use_case,
    get_list_active_reservations_use_case,
    get_browse_steward_reservations_use_case,
    get_list_confirmed_reservations_use_case,
    get_list_game_copies_use_case,
    get_browse_game_copies_use_case,
    get_list_incidents_for_game_copy_use_case,
    get_list_incidents_use_case,
    get_list_seated_reservations_use_case,
    get_no_show_reservation_use_case,
    get_report_incident_use_case,
    get_delete_incident_use_case,
    get_seat_reservation_use_case,
    get_swap_game_copy_use_case,
    get_update_game_copy_status_use_case,
    get_update_reservation_use_case,
    get_list_waitlist_use_case,
    get_add_waitlist_use_case,
    get_remove_waitlist_use_case,
)

bp = Blueprint("steward", __name__, url_prefix="/api/steward")


def _require_staff():
    if not current_user.is_authenticated:
        return {"error": "Authentication required"}, 401
    if current_user.role not in ("staff", "admin"):
        return {"error": "Staff access required"}, 403
    return None


def _serialize_reservation(reservation):
    return {
        "id": reservation.id,
        "customer_id": reservation.customer_id,
        "customer_name": getattr(reservation, "customer_name", None),
        "customer_email": getattr(reservation, "customer_email", None),
        "table_id": getattr(reservation, "table_id", None),
        "start_ts": reservation.start_ts.isoformat() if hasattr(reservation.start_ts, "isoformat") else reservation.start_ts,
        "end_ts": reservation.end_ts.isoformat() if hasattr(reservation.end_ts, "isoformat") else reservation.end_ts,
        "party_size": reservation.party_size,
        "status": reservation.status,
        "notes": reservation.notes,
    }


def _serialize_game_copy(game_copy):
    return {
        "id": game_copy.id,
        "game_id": game_copy.game_id,
        "game_title": getattr(game_copy, "game_title", None),
        "copy_code": game_copy.copy_code,
        "status": game_copy.status,
        "location": game_copy.location,
        "condition_note": game_copy.condition_note,
    }


def _serialize_incident(incident):
    return {
        "id": incident.id,
        "game_copy_id": incident.game_copy_id,
        "reported_by": incident.reported_by,
        "incident_type": incident.incident_type,
        "note": incident.note,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
    }


def _serialize_reservation_game(reservation_game):
    return {
        "id": reservation_game.id,
        "booking_id": reservation_game.booking_id,
        "requested_game_id": reservation_game.requested_game_id,
        "game_copy_id": reservation_game.game_copy_id,
    }


def _serialize_waitlist_entry(entry):
    return {
        "id": entry.id,
        "customer_id": entry.customer_id,
        "party_size": entry.party_size,
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat() if getattr(entry, "created_at", None) else None,
    }


# -----------------------------------------------------------------------
# Workflow 2 — View reservations
# -----------------------------------------------------------------------

@bp.get("/reservations")
@login_required
def list_active_reservations():
    err = _require_staff()
    if err:
        return err

    date_str = request.args.get("date")
    reservation_date = None
    if date_str:
        try:
            from datetime import datetime

            reservation_date = datetime.fromisoformat(date_str).date()
        except Exception:
            reservation_date = None

    use_case: BrowseStewardReservationsUseCase = get_browse_steward_reservations_use_case()
    items = use_case.execute(
        BrowseStewardReservationsQuery(
            statuses=("confirmed",),
            reservation_date=reservation_date,
        )
    )
    return [_serialize_reservation(r) for r in items], 200


@bp.get("/reservations/confirmed")
@login_required
def list_confirmed_reservations():
    err = _require_staff()
    if err:
        return err

    date_str = request.args.get("date")
    reservation_date = None
    if date_str:
        try:
            from datetime import datetime

            reservation_date = datetime.fromisoformat(date_str).date()
        except Exception:
            reservation_date = None

    use_case: BrowseStewardReservationsUseCase = get_browse_steward_reservations_use_case()
    items = use_case.execute(
        BrowseStewardReservationsQuery(
            statuses=("confirmed",),
            reservation_date=reservation_date,
        )
    )
    return [_serialize_reservation(r) for r in items], 200


@bp.get("/reservations/seated")
@login_required
def list_seated_reservations():
    err = _require_staff()
    if err:
        return err

    date_str = request.args.get("date")
    reservation_date = None
    if date_str:
        try:
            from datetime import datetime

            reservation_date = datetime.fromisoformat(date_str).date()
        except Exception:
            reservation_date = None

    use_case: BrowseStewardReservationsUseCase = get_browse_steward_reservations_use_case()
    items = use_case.execute(
        BrowseStewardReservationsQuery(
            statuses=("seated",),
            reservation_date=reservation_date,
        )
    )
    return [_serialize_reservation(r) for r in items], 200


# -----------------------------------------------------------------------
# Workflow 3 — Seat parties / update status
# -----------------------------------------------------------------------

def _run_status_transition(use_case, reservation_id: int):
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


@bp.patch("/reservations/<int:reservation_id>/seat")
@login_required
def seat_reservation(reservation_id: int):
    err = _require_staff()
    if err:
        return err

    use_case: SeatBookingUseCase = get_seat_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch("/reservations/<int:reservation_id>/complete")
@login_required
def complete_reservation(reservation_id: int):
    err = _require_staff()
    if err:
        return err

    use_case: CompleteBookingUseCase = get_complete_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch("/reservations/<int:reservation_id>/no-show")
@login_required
def no_show_reservation(reservation_id: int):
    err = _require_staff()
    if err:
        return err

    use_case: MarkBookingNoShowUseCase = get_no_show_reservation_use_case()
    return _run_status_transition(use_case, reservation_id)


@bp.patch('/reservations/<int:reservation_id>')
@login_required
def update_reservation(reservation_id: int):
    err = _require_staff()
    if err:
        return err

    data = request.get_json() or {}
    use_case = get_update_reservation_use_case()
    try:
        reservation = use_case.execute(reservation_id, data)
    except (DomainError, ValueError) as exc:
        return {"error": str(exc)}, 400

    if reservation is None:
        return {"error": "Reservation not found"}, 404

    return _serialize_reservation(reservation), 200


# -----------------------------------------------------------------------
# Workflow 4 — Swap games
# -----------------------------------------------------------------------

@bp.patch("/reservations/<int:reservation_id>/games/<int:reservation_game_id>/swap")
@login_required
def swap_game_copy(reservation_id: int, reservation_game_id: int):
    err = _require_staff()
    if err:
        return err

    data = request.get_json() or {}
    new_copy_id = data.get("new_copy_id")
    if not new_copy_id:
        return {"error": "new_copy_id is required"}, 400

    use_case: SwapGameCopyUseCase = get_swap_game_copy_use_case()
    try:
        reservation_game = use_case.execute(reservation_game_id, new_copy_id)
    except (DomainError, ValueError) as exc:
        return {"error": str(exc)}, 400

    return _serialize_reservation_game(reservation_game), 200


# -----------------------------------------------------------------------
# Workflow 5 — Check out / check in game copies
# -----------------------------------------------------------------------

@bp.get("/game-copies")
@login_required
def list_game_copies():
    err = _require_staff()
    if err:
        return err

    game_id = request.args.get("game_id", type=int)
    query_text = request.args.get("q") or ""

    browse_use_case: BrowseGameCopiesUseCase = get_browse_game_copies_use_case()
    items = browse_use_case.execute(
        BrowseGameCopiesQuery(game_id=game_id, search_text=query_text)
    )

    return [_serialize_game_copy(item) for item in items], 200


@bp.patch("/game-copies/<int:copy_id>/status")
@login_required
def update_game_copy_status(copy_id: int):
    err = _require_staff()
    if err:
        return err

    data = request.get_json() or {}
    action = data.get("action")
    if not action:
        return {"error": "action is required"}, 400

    use_case: UpdateGameCopyStatusUseCase = get_update_game_copy_status_use_case()
    try:
        game_copy = use_case.execute(copy_id, action)
    except (DomainError, ValueError) as exc:
        return {"error": str(exc)}, 400

    # Publish realtime event so dashboards update live
    try:
        publish_realtime_event({"event_type": "game_copy.updated", "data": _serialize_game_copy(game_copy)})
    except Exception:
        # best-effort: don't fail the request if realtime publish isn't available
        pass

    return _serialize_game_copy(game_copy), 200


# -----------------------------------------------------------------------
# Workflow 6 — Incidents
# -----------------------------------------------------------------------

@bp.post("/game-copies/<int:copy_id>/incidents")
@login_required
def report_incident(copy_id: int):
    err = _require_staff()
    if err:
        return err

    data = request.get_json() or {}
    incident_type = data.get("incident_type")
    note = data.get("note")

    if not incident_type or not note:
        return {"error": "incident_type and note are required"}, 400

    use_case: ReportIncidentUseCase = get_report_incident_use_case()
    try:
        incident = use_case.execute(
            game_copy_id=copy_id,
            steward_id=current_user.id,
            incident_type=incident_type,
            note=note,
        )
    except (DomainError, ValueError) as exc:
        return {"error": str(exc)}, 400

    # Publish realtime event for new incident (best-effort)
    try:
        publish_realtime_event({"event_type": "incident.created", "data": _serialize_incident(incident)})
    except Exception:
        pass

    return _serialize_incident(incident), 201


@bp.get("/game-copies/<int:copy_id>/incidents")
@login_required
def list_incidents_for_game_copy(copy_id: int):
    err = _require_staff()
    if err:
        return err

    use_case: ListIncidentsForGameCopyUseCase = get_list_incidents_for_game_copy_use_case()
    incidents = use_case.execute(copy_id)
    return [_serialize_incident(i) for i in incidents], 200


@bp.get("/incidents")
@login_required
def list_all_incidents():
    err = _require_staff()
    if err:
        return err

    date_str = request.args.get('date')
    use_case: ListIncidentsUseCase = get_list_incidents_use_case()
    incidents = use_case.execute()
    if date_str:
        try:
            from datetime import datetime
            d = datetime.fromisoformat(date_str).date()
            incidents = [i for i in incidents if getattr(i, 'created_at', None) and i.created_at.date() == d]
        except Exception:
            pass
    return [_serialize_incident(i) for i in incidents], 200


@bp.delete("/incidents/<int:incident_id>")
@login_required
def delete_incident(incident_id: int):
    err = _require_staff()
    if err:
        return err

    use_case = get_delete_incident_use_case()
    ok = use_case.execute(incident_id)
    if not ok:
        return {"error": "Not found"}, 404
    try:
        publish_realtime_event({"event_type": "incident.deleted", "data": {"id": incident_id}})
    except Exception:
        pass
    return {}, 204


@bp.get("/waitlist")
@login_required
def list_waitlist():
    err = _require_staff()
    if err:
        return err

    use_case: ListWaitlistUseCase = get_list_waitlist_use_case()
    entries = use_case.execute()
    return [_serialize_waitlist_entry(e) for e in entries], 200


@bp.post("/waitlist")
@login_required
def add_waitlist_entry():
    err = _require_staff()
    if err:
        return err

    data = request.get_json() or {}
    customer_id = data.get("customer_id")
    party_size = data.get("party_size")
    notes = data.get("notes")
    if not customer_id or not party_size:
        return {"error": "customer_id and party_size are required"}, 400

    use_case: AddToWaitlistUseCase = get_add_waitlist_use_case()
    entry = use_case.execute(
        type("C", (), {"customer_id": customer_id, "party_size": party_size, "notes": notes})
    )
    return _serialize_waitlist_entry(entry), 201


@bp.delete("/waitlist/<int:entry_id>")
@login_required
def remove_waitlist_entry(entry_id: int):
    err = _require_staff()
    if err:
        return err

    use_case: RemoveFromWaitlistUseCase = get_remove_waitlist_use_case()
    ok = use_case.execute(entry_id)
    if not ok:
        return {"error": "Not found"}, 404
    return {}, 204