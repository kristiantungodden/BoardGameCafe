from __future__ import annotations

from typing import Any, Protocol


class AdminReportsPortInterface(Protocol):
    def dashboard_stats(self) -> dict[str, Any]:
        ...

    def registrations_report(self, days: int) -> list[dict[str, Any]]:
        ...

    def revenue_report(self, days: int) -> list[dict[str, Any]]:
        ...

    def top_games_report(self, days: int) -> dict[str, list[dict[str, Any]]]:
        ...

    def revenue_csv(self, days: int) -> tuple[str, str]:
        ...
