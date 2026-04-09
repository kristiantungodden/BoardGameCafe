from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
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

            floor_groups[table.floor][table.zone or "Unzoned"].append(
                {
                    "id": table.id,
                    "table_nr": str(table.number),
                    "capacity": table.capacity,
                    "floor": table.floor,
                    "zone": table.zone,
                    "status": table.status,
                    "available": len(reasons) == 0,
                    "unavailable_reasons": reasons,
                }
            )

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

        return {
            "filters": {
                "start_ts": start_ts.isoformat(),
                "end_ts": end_ts.isoformat(),
                "party_size": party_size,
                "floor": floor,
            },
            "floors": floors,
        }