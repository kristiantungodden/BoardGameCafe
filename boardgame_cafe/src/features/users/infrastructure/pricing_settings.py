from __future__ import annotations

from datetime import datetime, timezone

from features.users.infrastructure.database.admin_policy_db import AdminPolicyDB


def _now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _get_or_create_policy(session) -> AdminPolicyDB:
    policy = session.get(AdminPolicyDB, 1)
    if policy is not None:
        return policy

    policy = AdminPolicyDB(
        id=1,
        booking_base_fee_cents=2500,
        booking_base_fee_priority=0,
        booking_base_fee_override_cents=None,
        booking_base_fee_override_priority=100,
        booking_base_fee_override_until_epoch=None,
        booking_cancel_time_limit_hours=24,
    )
    session.add(policy)
    session.flush()
    return policy


def resolve_base_fee(session, cleanup_expired: bool = False) -> dict:
    policy = _get_or_create_policy(session)
    changed = False

    override_fee = policy.booking_base_fee_override_cents
    override_until = policy.booking_base_fee_override_until_epoch

    if (
        cleanup_expired
        and override_fee is not None
        and override_until is not None
        and int(override_until) <= _now_epoch()
    ):
        policy.booking_base_fee_override_cents = None
        policy.booking_base_fee_override_until_epoch = None
        override_fee = None
        override_until = None
        changed = True

    override_is_active = bool(
        override_fee is not None
        and (override_until is None or int(override_until) > _now_epoch())
    )

    base_fee = int(policy.booking_base_fee_cents or 0)
    base_priority = int(policy.booking_base_fee_priority or 0)
    override_priority = int(policy.booking_base_fee_override_priority or 0)

    if override_is_active and override_priority >= base_priority:
        effective_fee = int(override_fee)
        effective_priority = override_priority
    else:
        effective_fee = base_fee
        effective_priority = base_priority

    return {
        "changed": changed,
        "effective_fee_cents": effective_fee,
        "effective_priority": effective_priority,
        "base_fee_cents": base_fee,
        "base_priority": base_priority,
        "override_fee_cents": None if override_fee is None else int(override_fee),
        "override_priority": override_priority,
        "active_until_epoch": None if override_until is None else int(override_until),
        "override_is_active": override_is_active,
        "booking_cancel_time_limit_hours": int(policy.booking_cancel_time_limit_hours or 24),
    }


def configure_base_fee(
    session,
    value: int,
    *,
    active_until_epoch: int | None = None,
    priority: int = 0,
) -> None:
    policy = _get_or_create_policy(session)

    if active_until_epoch is None:
        policy.booking_base_fee_cents = int(value)
        policy.booking_base_fee_priority = int(priority)
        policy.booking_base_fee_override_cents = None
        policy.booking_base_fee_override_until_epoch = None
        return

    policy.booking_base_fee_override_cents = int(value)
    policy.booking_base_fee_override_priority = int(priority)
    policy.booking_base_fee_override_until_epoch = int(active_until_epoch)


def set_cancel_time_limit_hours(session, hours: int) -> None:
    policy = _get_or_create_policy(session)
    policy.booking_cancel_time_limit_hours = int(hours)
