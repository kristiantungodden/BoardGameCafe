from __future__ import annotations

from typing import Any

from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.incident_db import IncidentDB
from shared.infrastructure import db


class SqlAlchemyAdminIncidentAdapter:
    def copy_exists(self, copy_id: int) -> bool:
        return db.session.get(GameCopyDB, copy_id) is not None

    def list_copy_incidents(self, copy_id: int) -> list[dict[str, Any]]:
        rows = (
            db.session.query(IncidentDB)
            .filter(IncidentDB.game_copy_id == copy_id)
            .order_by(IncidentDB.created_at.desc(), IncidentDB.id.desc())
            .all()
        )
        return [self._serialize_incident(row) for row in rows]

    def list_incidents(self) -> list[dict[str, Any]]:
        rows = (
            db.session.query(IncidentDB)
            .order_by(IncidentDB.created_at.desc(), IncidentDB.id.desc())
            .all()
        )
        return [self._serialize_incident(row) for row in rows]

    def resolve_incident(self, incident_id: int) -> dict[str, Any] | None:
        incident = db.session.get(IncidentDB, incident_id)
        if incident is None:
            return None

        copy_row = db.session.get(GameCopyDB, int(incident.game_copy_id))
        if copy_row is None:
            raise LookupError("Game copy not found")

        copy_row.status = "available"
        db.session.delete(incident)
        db.session.commit()

        return {
            "message": "Incident resolved",
            "copy": self._serialize_copy(copy_row),
        }

    @staticmethod
    def _serialize_incident(row: IncidentDB) -> dict[str, Any]:
        steward = getattr(row, "steward", None)
        game_copy = getattr(row, "game_copy", None)
        game = getattr(game_copy, "game", None) if game_copy is not None else None
        return {
            "id": int(row.id),
            "game_copy_id": int(row.game_copy_id),
            "game_copy_code": getattr(game_copy, "copy_code", None),
            "game_title": getattr(game, "title", None),
            "reported_by": int(row.reported_by),
            "reported_by_name": getattr(steward, "name", None),
            "incident_type": row.incident_type,
            "note": row.note,
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
        }

    @staticmethod
    def _serialize_copy(row: GameCopyDB) -> dict[str, Any]:
        game = getattr(row, "game", None)
        return {
            "id": int(row.id),
            "game_id": int(row.game_id),
            "game_title": getattr(game, "title", None),
            "copy_code": row.copy_code,
            "status": row.status,
            "location": row.location,
            "condition_note": row.condition_note,
            "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
        }
