from __future__ import annotations

from typing import Any, Protocol


class AdminPricingPortInterface(Protocol):
    def get_pricing(self) -> dict[str, Any]:
        ...

    def update_base_fee(
        self,
        booking_base_fee_cents: int,
        booking_cancel_time_limit_hours: int,
        booking_base_fee_active_until_epoch: int | None,
    ) -> dict[str, Any]:
        ...

    def update_table_price(self, table_id: int, price_cents: int) -> dict[str, Any] | None:
        ...

    def update_game_price(self, game_id: int, price_cents: int) -> dict[str, Any] | None:
        ...
