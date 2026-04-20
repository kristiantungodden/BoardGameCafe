from flask import Blueprint, Response, stream_with_context, current_app
from flask_login import login_required

from shared.infrastructure.message_bus.realtime import stream_realtime_events
from shared.infrastructure import db

bp = Blueprint("events", __name__, url_prefix="/api")


@bp.route("/events/stream", methods=["GET"])
@login_required
def realtime_event_stream():
    try:
        response = Response(
            stream_with_context(stream_realtime_events()),
            mimetype="text/event-stream",
        )
    except RuntimeError as exc:
        return {"error": str(exc)}, 503

    # Release the SQLAlchemy session here — the request will remain open
    # for the SSE stream and holding a DB connection would exhaust the pool.
    try:
        db.session.remove()
    except Exception:
        current_app.logger.debug('Failed to remove DB session for SSE stream', exc_info=True)

    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
