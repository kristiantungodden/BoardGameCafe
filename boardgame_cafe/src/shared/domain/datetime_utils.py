from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


UTC = timezone.utc
APP_TIMEZONE = ZoneInfo("Europe/Oslo")


def to_utc_aware(ts: datetime) -> datetime:
    """Normalize a timestamp to timezone-aware UTC.

    Naive timestamps are treated as UTC to preserve existing persisted semantics.
    """
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def to_utc_naive(ts: datetime) -> datetime:
    """Normalize a timestamp to naive UTC for DB operations."""
    return to_utc_aware(ts).replace(tzinfo=None)


def to_app_local(ts: datetime) -> datetime:
    """Convert timestamp into application local timezone (Europe/Oslo)."""
    return to_utc_aware(ts).astimezone(APP_TIMEZONE)


def format_utc_iso(ts: datetime) -> str:
    """Serialize timestamp as ISO-8601 UTC string with Z suffix."""
    return to_utc_aware(ts).isoformat().replace("+00:00", "Z")
