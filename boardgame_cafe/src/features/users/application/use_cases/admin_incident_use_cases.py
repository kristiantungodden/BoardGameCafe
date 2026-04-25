from __future__ import annotations

from typing import Any

from features.users.application.interfaces.admin_incident_port_interface import (
    AdminIncidentPortInterface,
)


class IncidentResolutionUseCase:
    def __init__(self, port: AdminIncidentPortInterface):
        self.port = port

    def list_copy_incidents(self, copy_id: int) -> list[dict[str, Any]]:
        if not self.port.copy_exists(copy_id):
            raise LookupError("Game copy not found")
        return self.port.list_copy_incidents(copy_id)

    def list_incidents(self) -> list[dict[str, Any]]:
        return self.port.list_incidents()

    def resolve_incident(self, incident_id: int) -> dict[str, Any]:
        payload = self.port.resolve_incident(incident_id)
        if payload is None:
            raise LookupError("Incident not found")
        return payload
