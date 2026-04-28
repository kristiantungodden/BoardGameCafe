from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from features.users.infrastructure.database.admin_policy_db import AdminPolicyDB

BASE_FEE_DEFAULT = 2500
CANCEL_TIME_LIMIT_DEFAULT_HOURS = 24


def _coerce_int(value, default: int) -> int:
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _get_or_create_policy(session) -> AdminPolicyDB:
    row = session.get(AdminPolicyDB, 1)
    if row is not None:
        return row

    row = AdminPolicyDB(
        id=1,
        booking_base_fee_cents=BASE_FEE_DEFAULT,
        booking_base_fee_override_cents=None,
        booking_base_fee_override_until_epoch=None,
        booking_cancel_time_limit_hours=CANCEL_TIME_LIMIT_DEFAULT_HOURS,
    )
    session.add(row)
    return row


def _to_utc_epoch_seconds(now: Optional[datetime]) -> int:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    return int(current.timestamp())


def configure_base_fee(
    session,
    cents: int,
    active_until_epoch: Optional[int] = None,
) -> None:
    row = _get_or_create_policy(session)

    if active_until_epoch is None:
        row.booking_base_fee_cents = int(cents)
        row.booking_base_fee_override_cents = None
        row.booking_base_fee_override_until_epoch = None
        return

    row.booking_base_fee_override_cents = int(cents)
    row.booking_base_fee_override_until_epoch = int(active_until_epoch)


def set_cancel_time_limit_hours(session, hours: int) -> None:
    row = _get_or_create_policy(session)
    row.booking_cancel_time_limit_hours = int(hours)


def resolve_base_fee(
    session,
    now: Optional[datetime] = None,
    cleanup_expired: bool = False,
) -> dict:
    row = _get_or_create_policy(session)
    base_fee = _coerce_int(
        getattr(row, "booking_base_fee_cents", BASE_FEE_DEFAULT),
        BASE_FEE_DEFAULT,
    )
    override_fee = getattr(row, "booking_base_fee_override_cents", None)
    override_until = getattr(row, "booking_base_fee_override_until_epoch", None)
    cancel_limit_hours = _coerce_int(
        getattr(row, "booking_cancel_time_limit_hours", CANCEL_TIME_LIMIT_DEFAULT_HOURS),
        CANCEL_TIME_LIMIT_DEFAULT_HOURS,
    )
    now_epoch = _to_utc_epoch_seconds(now)

    changed = False
    override_is_active = (
        override_fee is not None
        and override_until is not None
        and now_epoch <= override_until
    )

    if cleanup_expired and override_until is not None and now_epoch > override_until:
        row.booking_base_fee_override_cents = None
        row.booking_base_fee_override_until_epoch = None
        changed = True
        override_is_active = False

    effective_fee = int(base_fee)
    active_until_epoch: Optional[int] = None

    if override_is_active:
        effective_fee = int(override_fee)
        active_until_epoch = int(override_until)

    return {
        "effective_fee_cents": int(effective_fee),
        "base_fee_cents": int(base_fee),
        "override_fee_cents": int(override_fee) if override_fee is not None else None,
        "active_until_epoch": active_until_epoch,
        "override_is_active": bool(active_until_epoch is not None),
        "booking_cancel_time_limit_hours": int(cancel_limit_hours),
        "changed": changed,
    }
