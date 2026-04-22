from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Optional

from features.reservations.application.interfaces.reservation_repository_interface import (
    ReservationRepositoryInterface,
)
from features.tables.application.interfaces.table_repository import (
    TableFilters,
    TableRepository,
)
from shared.domain.constants import OVERLAP_BLOCKING_STATUSES


@dataclass(frozen=True)
class TableAvailabilityQuery:
    start_ts: datetime
    end_ts: datetime
    party_size: int
    floor: Optional[int] = None


class GetTableAvailabilityUseCase:
    def __init__(
        self,
        table_repo: TableRepository,
        reservation_repo: ReservationRepositoryInterface,
    ) -> None:
        self.table_repo = table_repo
        self.reservation_repo = reservation_repo

    def execute(
        self,
        start_ts: datetime,
        end_ts: datetime,
        party_size: int,
        floor: Optional[int] = None,
    ) -> dict:
        tables = self.table_repo.search(TableFilters(floor=floor))

        floor_groups: dict[int, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
        combinable_tables: list[dict] = []
        for table in sorted(tables, key=lambda item: (item.floor, item.zone or "", item.number)):
            reasons: list[str] = []

            if table.capacity < party_size:
                reasons.append("capacity")

            if table.status != "available":
                reasons.append("table_status")

            overlapping_reservations = self.reservation_repo.list_for_table_in_window(
                table.id,
                start_ts,
                end_ts,
            )
            if any(reservation.status in OVERLAP_BLOCKING_STATUSES for reservation in overlapping_reservations):
                reasons.append("reservation_overlap")

            table_payload = {
                "id": table.id,
                "table_nr": str(table.number),
                "capacity": table.capacity,
                "price_cents": int(getattr(table, "price_cents", 15000) or 0),
                "floor": table.floor,
                "zone": table.zone,
                "status": table.status,
                "available": len(reasons) == 0,
                "selectable": len(reasons) == 0 or reasons == ["capacity"],
                "unavailable_reasons": reasons,
            }
            floor_groups[table.floor][table.zone or "Unzoned"].append(table_payload)

            if table_payload["selectable"]:
                combinable_tables.append(table_payload)

        floors = []
        for floor_number in sorted(floor_groups):
            zones = []
            for zone_name in sorted(floor_groups[floor_number]):
                zones.append(
                    {
                        "zone": zone_name,
                        "tables": sorted(
                            floor_groups[floor_number][zone_name],
                            key=lambda item: (item["table_nr"], item["id"] or 0),
                        ),
                    }
                )
            floors.append({"floor": floor_number, "zones": zones})

        suggested_tables = self._select_table_combination(combinable_tables, party_size)

        return {
            "filters": {
                "start_ts": start_ts.isoformat(),
                "end_ts": end_ts.isoformat(),
                "party_size": party_size,
                "floor": floor,
            },
            "floors": floors,
            "suggested_tables": suggested_tables,
        }

    @staticmethod
    def _select_table_combination(available_tables: list[dict], party_size: int) -> list[dict]:
        if party_size <= 0 or not available_tables:
            return []

        ordered = sorted(
            available_tables,
            key=lambda item: (item["capacity"], item["floor"], item["table_nr"], item["id"]),
        )

        best_combo = None
        best_key = None

        for combo_size in range(1, len(ordered) + 1):
            for combo in combinations(ordered, combo_size):
                total_capacity = sum(item["capacity"] for item in combo)
                if total_capacity < party_size:
                    continue

                combo_ids = tuple(sorted(item["id"] for item in combo))
                candidate_key = (combo_size, total_capacity, combo_ids)

                if best_key is None or candidate_key < best_key:
                    best_key = candidate_key
                    best_combo = combo

            if best_combo is not None:
                break

        if best_combo is None:
            return []

        return [
            {
                "id": item["id"],
                "table_nr": item["table_nr"],
                "capacity": item["capacity"],
                "price_cents": int(item.get("price_cents", 0) or 0),
                "floor": item["floor"],
                "zone": item["zone"],
                "status": item["status"],
            }
            for item in sorted(best_combo, key=lambda table: (table["capacity"], table["id"]))
        ]