from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from features.games.infrastructure.database.game_db import GameDB
from features.tables.infrastructure.database.table_db import TableDB
from features.users.infrastructure.pricing_settings import (
    configure_base_fee,
    resolve_base_fee,
    set_cancel_time_limit_hours,
)
from shared.infrastructure import db


class SqlAlchemyAdminPricingAdapter:
    def get_pricing(self) -> dict[str, Any]:
        fee_state = resolve_base_fee(
            db.session,
            cleanup_expired=True,
        )
        if fee_state["changed"]:
            db.session.commit()

        table_rows = db.session.query(TableDB).order_by(TableDB.floor.asc(), TableDB.table_nr.asc()).all()
        game_rows = db.session.query(GameDB).order_by(GameDB.title.asc()).all()

        return {
            "booking_base_fee_cents": int(fee_state["effective_fee_cents"]),
            "booking_base_fee_priority": int(fee_state["effective_priority"]),
            "booking_base_fee_default_cents": int(fee_state["base_fee_cents"]),
            "booking_base_fee_default_priority": int(fee_state["base_priority"]),
            "booking_base_fee_override_cents": fee_state["override_fee_cents"],
            "booking_base_fee_override_priority": int(fee_state["override_priority"]),
            "booking_base_fee_active_until": self._epoch_to_iso(fee_state["active_until_epoch"]),
            "booking_base_fee_has_temporary_override": bool(fee_state["override_is_active"]),
            "booking_cancel_time_limit_hours": int(fee_state["booking_cancel_time_limit_hours"]),
            "tables": [
                {
                    "id": row.id,
                    "table_nr": row.table_nr,
                    "floor": row.floor,
                    "zone": row.zone,
                    "capacity": row.capacity,
                    "price_cents": int(getattr(row, "price_cents", 0) or 0),
                }
                for row in table_rows
            ],
            "games": [
                {
                    "id": row.id,
                    "title": row.title,
                    "price_cents": int(getattr(row, "price_cents", 0) or 0),
                }
                for row in game_rows
            ],
        }

    def update_base_fee(
        self,
        booking_base_fee_cents: int,
        booking_base_fee_priority: int,
        booking_cancel_time_limit_hours: int,
        booking_base_fee_active_until_epoch: int | None,
    ) -> dict[str, Any]:
        configure_base_fee(
            db.session,
            booking_base_fee_cents,
            active_until_epoch=booking_base_fee_active_until_epoch,
            priority=booking_base_fee_priority,
        )
        set_cancel_time_limit_hours(db.session, booking_cancel_time_limit_hours)
        db.session.commit()
        fee_state = resolve_base_fee(db.session)
        return {
            "booking_base_fee_cents": int(fee_state["effective_fee_cents"]),
            "booking_base_fee_priority": int(fee_state["effective_priority"]),
            "booking_base_fee_default_cents": int(fee_state["base_fee_cents"]),
            "booking_base_fee_default_priority": int(fee_state["base_priority"]),
            "booking_base_fee_override_cents": fee_state["override_fee_cents"],
            "booking_base_fee_override_priority": int(fee_state["override_priority"]),
            "booking_base_fee_active_until": self._epoch_to_iso(fee_state["active_until_epoch"]),
            "booking_base_fee_has_temporary_override": bool(fee_state["override_is_active"]),
            "booking_cancel_time_limit_hours": int(fee_state["booking_cancel_time_limit_hours"]),
        }

    def update_table_price(self, table_id: int, price_cents: int) -> dict[str, Any] | None:
        row = db.session.get(TableDB, table_id)
        if row is None:
            return None

        row.price_cents = price_cents
        db.session.commit()
        return {"id": row.id, "price_cents": int(row.price_cents)}

    def update_game_price(self, game_id: int, price_cents: int) -> dict[str, Any] | None:
        row = db.session.get(GameDB, game_id)
        if row is None:
            return None

        row.price_cents = price_cents
        db.session.commit()
        return {"id": row.id, "price_cents": int(row.price_cents)}

    @staticmethod
    def _epoch_to_iso(value: int | None) -> str | None:
        if value is None:
            return None
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
