from __future__ import annotations

from typing import Any

from features.users.application.interfaces.admin_catalogue_port_interface import (
    AdminCataloguePortInterface,
)


class ConflictError(Exception):
    pass


class CatalogueManagementUseCase:
    def __init__(self, port: AdminCataloguePortInterface):
        self.port = port

    def get_overview(self, query_text: str | None = None) -> dict[str, list[dict[str, Any]]]:
        return self.port.list_catalogue(query_text)

    def create_game(self, raw: dict[str, Any]) -> dict[str, Any]:
        title = str(raw.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")

        min_players = self._parse_non_negative_int(raw.get("min_players"), "min_players")
        max_players = self._parse_non_negative_int(raw.get("max_players"), "max_players")
        playtime_min = self._parse_non_negative_int(raw.get("playtime_min"), "playtime_min")
        if min_players < 1 or max_players < 1:
            raise ValueError("min_players and max_players must be at least 1")
        if min_players > max_players:
            raise ValueError("min_players cannot exceed max_players")

        complexity = self._parse_non_negative_float(raw.get("complexity"), "complexity")
        if complexity > 5:
            raise ValueError("complexity must be between 0 and 5")

        price_cents = self._parse_non_negative_int(raw.get("price_cents", 0), "price_cents")
        description = raw.get("description")
        image_url = raw.get("image_url")

        return self.port.create_game(
            {
                "title": title,
                "min_players": min_players,
                "max_players": max_players,
                "playtime_min": playtime_min,
                "price_cents": price_cents,
                "complexity": complexity,
                "description": description,
                "image_url": image_url,
            }
        )

    def update_game(self, game_id: int, raw: dict[str, Any]) -> dict[str, Any]:
        if not self.port.game_exists(game_id):
            raise LookupError("Game not found")

        if not raw:
            raise ValueError("At least one field must be provided")

        update_payload: dict[str, Any] = {}
        current = self.port.get_game(game_id)
        if current is None:
            raise LookupError("Game not found")

        min_players = int(current["min_players"])
        max_players = int(current["max_players"])

        if "title" in raw:
            title = str(raw.get("title") or "").strip()
            if not title:
                raise ValueError("title cannot be blank")
            update_payload["title"] = title

        if "min_players" in raw:
            min_players = self._parse_non_negative_int(raw.get("min_players"), "min_players")
            update_payload["min_players"] = min_players
        if "max_players" in raw:
            max_players = self._parse_non_negative_int(raw.get("max_players"), "max_players")
            update_payload["max_players"] = max_players
        if min_players < 1 or max_players < 1:
            raise ValueError("min_players and max_players must be at least 1")
        if min_players > max_players:
            raise ValueError("min_players cannot exceed max_players")

        if "playtime_min" in raw:
            update_payload["playtime_min"] = self._parse_non_negative_int(raw.get("playtime_min"), "playtime_min")
        if "price_cents" in raw:
            update_payload["price_cents"] = self._parse_non_negative_int(raw.get("price_cents"), "price_cents")
        if "complexity" in raw:
            complexity = self._parse_non_negative_float(raw.get("complexity"), "complexity")
            if complexity > 5:
                raise ValueError("complexity must be between 0 and 5")
            update_payload["complexity"] = complexity
        if "description" in raw:
            update_payload["description"] = raw.get("description")
        if "image_url" in raw:
            update_payload["image_url"] = raw.get("image_url")

        updated = self.port.update_game(game_id, update_payload)
        if updated is None:
            raise LookupError("Game not found")
        return updated

    def delete_game(self, game_id: int) -> None:
        if not self.port.game_exists(game_id):
            raise LookupError("Game not found")

        copy_count = self.port.count_copies_for_game(game_id)
        if copy_count > 0:
            raise ConflictError("Delete copies for this game before deleting the game.")

        self.port.delete_game(game_id)

    def create_copy(self, raw: dict[str, Any]) -> dict[str, Any]:
        game_id = int(raw.get("game_id"))
        copy_code = str(raw.get("copy_code") or "").strip()
        if not copy_code:
            raise ValueError("copy_code is required")
        status = self._parse_copy_status(raw.get("status") or "available")
        location = raw.get("location")
        condition_note = raw.get("condition_note")

        if not self.port.game_exists(game_id):
            raise LookupError("Game not found")

        try:
            return self.port.create_copy(
                {
                    "game_id": game_id,
                    "copy_code": copy_code,
                    "status": status,
                    "location": location,
                    "condition_note": condition_note,
                }
            )
        except ConflictError:
            raise

    def update_copy(self, copy_id: int, raw: dict[str, Any]) -> dict[str, Any]:
        if not self.port.copy_exists(copy_id):
            raise LookupError("Game copy not found")

        if not raw:
            raise ValueError("At least one field must be provided")

        update_payload: dict[str, Any] = {}
        current = self.port.get_copy(copy_id)
        if current is None:
            raise LookupError("Game copy not found")

        if "copy_code" in raw:
            copy_code = str(raw.get("copy_code") or "").strip()
            if not copy_code:
                raise ValueError("copy_code cannot be blank")
            update_payload["copy_code"] = copy_code
        if "status" in raw:
            next_status = self._parse_copy_status(raw.get("status"))
            if current["status"] != "available" and next_status == "available":
                has_open_incidents = self.port.copy_has_any_incident(copy_id)
                if has_open_incidents:
                    raise ConflictError("Resolve incidents before setting copy to available.")
            update_payload["status"] = next_status
        if "location" in raw:
            update_payload["location"] = raw.get("location")
        if "condition_note" in raw:
            update_payload["condition_note"] = raw.get("condition_note")

        updated = self.port.update_copy(copy_id, update_payload)
        if updated is None:
            raise LookupError("Game copy not found")
        return updated

    def delete_copy(self, copy_id: int) -> None:
        if not self.port.delete_copy_and_incidents(copy_id):
            raise LookupError("Game copy not found")

    @staticmethod
    def _parse_non_negative_int(value: Any, field_name: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be an integer") from exc
        if parsed < 0:
            raise ValueError(f"{field_name} must be non-negative")
        return parsed

    @staticmethod
    def _parse_non_negative_float(value: Any, field_name: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a number") from exc
        if parsed < 0:
            raise ValueError(f"{field_name} must be non-negative")
        return parsed

    @staticmethod
    def _parse_copy_status(value: Any) -> str:
        allowed = {"available", "reserved", "in_use", "maintenance", "lost", "occupied"}
        status = str(value or "").strip().lower()
        if status not in allowed:
            raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
        return status

