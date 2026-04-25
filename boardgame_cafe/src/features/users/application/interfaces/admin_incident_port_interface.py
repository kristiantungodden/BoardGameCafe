from __future__ import annotations

from typing import Any, Protocol


class AdminIncidentPortInterface(Protocol):
    def copy_exists(self, copy_id: int) -> bool:
        ...

    def list_copy_incidents(self, copy_id: int) -> list[dict[str, Any]]:
        ...

    def list_incidents(self) -> list[dict[str, Any]]:
        ...

    def resolve_incident(self, incident_id: int) -> dict[str, Any] | None:
        ...
