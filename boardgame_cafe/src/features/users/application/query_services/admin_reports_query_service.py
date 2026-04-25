from __future__ import annotations

from typing import Any

from features.users.application.interfaces.admin_reports_port_interface import (
    AdminReportsPortInterface,
)


class AdminReportsQueryService:
    def __init__(self, port: AdminReportsPortInterface):
        self.port = port

    def registrations_report(self, days: int) -> list[dict[str, Any]]:
        return self.port.registrations_report(days)

    def revenue_report(self, days: int) -> list[dict[str, Any]]:
        return self.port.revenue_report(days)

    def top_games_report(self, days: int) -> dict[str, list[dict[str, Any]]]:
        return self.port.top_games_report(days)

    def revenue_csv(self, days: int) -> tuple[str, str]:
        return self.port.revenue_csv(days)

    @staticmethod
    def normalize_days(raw_days: str | None) -> int:
        try:
            days = int(raw_days or 30)
        except (ValueError, TypeError):
            days = 30
        return max(1, min(days, 365))