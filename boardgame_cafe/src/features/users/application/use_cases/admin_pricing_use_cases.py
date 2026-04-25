from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from features.users.application.interfaces.admin_pricing_port_interface import (
    AdminPricingPortInterface,
)


@dataclass(frozen=True)
class UpdateBaseFeeCommand:
    booking_base_fee_cents: int
    booking_base_fee_priority: int = 0
    booking_cancel_time_limit_hours: int = 24
    booking_base_fee_active_until: str | None = None


@dataclass(frozen=True)
class UpdatePriceCommand:
    price_cents: int


class PricingManagementUseCase:
    def __init__(self, port: AdminPricingPortInterface):
        self.port = port

    def get_pricing(self) -> dict:
        return self.port.get_pricing()

    def update_base_fee(self, cmd: UpdateBaseFeeCommand) -> dict:
        active_until_epoch = self._parse_optional_future_timestamp(cmd.booking_base_fee_active_until)

        return self.port.update_base_fee(
            booking_base_fee_cents=cmd.booking_base_fee_cents,
            booking_base_fee_priority=cmd.booking_base_fee_priority,
            booking_cancel_time_limit_hours=cmd.booking_cancel_time_limit_hours,
            booking_base_fee_active_until_epoch=active_until_epoch,
        )

    def update_table_price(self, table_id: int, cmd: UpdatePriceCommand) -> dict:
        updated = self.port.update_table_price(table_id, cmd.price_cents)
        if updated is None:
            raise LookupError("Table not found")
        return updated

    def update_game_price(self, game_id: int, cmd: UpdatePriceCommand) -> dict:
        updated = self.port.update_game_price(game_id, cmd.price_cents)
        if updated is None:
            raise LookupError("Game not found")
        return updated

    @staticmethod
    def _parse_optional_future_timestamp(value: str | None) -> int | None:
        if value in (None, ""):
            return None

        normalized = value.strip()
        if not normalized:
            return None

        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("booking_base_fee_active_until must be a valid ISO datetime") from exc

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)

        now = datetime.now(timezone.utc)
        if parsed <= now:
            raise ValueError("booking_base_fee_active_until must be in the future")

        return int(parsed.timestamp())

