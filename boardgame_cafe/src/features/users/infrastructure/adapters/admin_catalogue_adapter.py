from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from features.games.infrastructure.database.game_copy_db import GameCopyDB
from features.games.infrastructure.database.game_db import GameDB
from features.games.infrastructure.database.incident_db import IncidentDB
from features.users.application.use_cases.admin_catalogue_use_cases import ConflictError
from shared.infrastructure import db


class SqlAlchemyAdminCatalogueAdapter:
    def list_catalogue(self, query_text: str | None) -> dict[str, list[dict[str, Any]]]:
        query_text = (query_text or "").strip().lower()

        games_query = db.session.query(GameDB).order_by(GameDB.title.asc())
        if query_text:
            games_query = games_query.filter(GameDB.title.ilike(f"%{query_text}%"))
        games = games_query.all()

        copies_query = (
            db.session.query(GameCopyDB)
            .join(GameDB, GameDB.id == GameCopyDB.game_id)
            .order_by(GameCopyDB.copy_code.asc())
        )
        if query_text:
            copies_query = copies_query.filter(
                db.or_(
                    GameCopyDB.copy_code.ilike(f"%{query_text}%"),
                    GameDB.title.ilike(f"%{query_text}%"),
                    GameCopyDB.location.ilike(f"%{query_text}%"),
                )
            )
        copies = copies_query.all()

        return {
            "games": [self._serialize_game(game) for game in games],
            "copies": [self._serialize_copy(copy_row) for copy_row in copies],
        }

    def create_game(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = GameDB(**payload)
        db.session.add(row)
        db.session.commit()
        return self._serialize_game(row)

    def get_game(self, game_id: int) -> dict[str, Any] | None:
        row = db.session.get(GameDB, game_id)
        if row is None:
            return None
        return self._serialize_game(row)

    def update_game(self, game_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        row = db.session.get(GameDB, game_id)
        if row is None:
            return None

        for key, value in payload.items():
            setattr(row, key, value)
        db.session.commit()
        return self._serialize_game(row)

    def delete_game(self, game_id: int) -> bool:
        row = db.session.get(GameDB, game_id)
        if row is None:
            return False
        db.session.delete(row)
        db.session.commit()
        return True

    def count_copies_for_game(self, game_id: int) -> int:
        result = (
            db.session.query(func.count(GameCopyDB.id))
            .filter(GameCopyDB.game_id == game_id)
            .scalar()
        )
        return int(result or 0)

    def game_exists(self, game_id: int) -> bool:
        return db.session.get(GameDB, game_id) is not None

    def create_copy(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = GameCopyDB(**payload)
        db.session.add(row)
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise ConflictError("copy_code already exists") from exc
        return self._serialize_copy(row)

    def get_copy(self, copy_id: int) -> dict[str, Any] | None:
        row = db.session.get(GameCopyDB, copy_id)
        if row is None:
            return None
        return self._serialize_copy(row)

    def update_copy(self, copy_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        row = db.session.get(GameCopyDB, copy_id)
        if row is None:
            return None

        for key, value in payload.items():
            setattr(row, key, value)

        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise ConflictError("copy_code already exists") from exc
        return self._serialize_copy(row)

    def copy_exists(self, copy_id: int) -> bool:
        return db.session.get(GameCopyDB, copy_id) is not None

    def copy_has_any_incident(self, copy_id: int) -> bool:
        return (
            db.session.query(IncidentDB.id)
            .filter(IncidentDB.game_copy_id == copy_id)
            .first()
            is not None
        )

    def delete_copy_and_incidents(self, copy_id: int) -> bool:
        row = db.session.get(GameCopyDB, copy_id)
        if row is None:
            return False

        db.session.query(IncidentDB).filter(IncidentDB.game_copy_id == copy_id).delete()
        db.session.delete(row)
        db.session.commit()
        return True

    @staticmethod
    def _serialize_game(row: GameDB) -> dict[str, Any]:
        return {
            "id": int(row.id),
            "title": row.title,
            "min_players": int(row.min_players),
            "max_players": int(row.max_players),
            "playtime_min": int(row.playtime_min),
            "price_cents": int(getattr(row, "price_cents", 0) or 0),
            "complexity": float(row.complexity),
            "description": row.description,
            "image_url": row.image_url,
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
