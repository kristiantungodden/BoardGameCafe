from __future__ import annotations

from typing import Any, Protocol, Sequence


class AdminCataloguePortInterface(Protocol):
    def list_catalogue(self, query_text: str | None) -> dict[str, list[dict[str, Any]]]:
        ...

    def create_game(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def get_game(self, game_id: int) -> dict[str, Any] | None:
        ...

    def update_game(self, game_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        ...

    def delete_game(self, game_id: int) -> bool:
        ...

    def count_copies_for_game(self, game_id: int) -> int:
        ...

    def game_exists(self, game_id: int) -> bool:
        ...

    def create_copy(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def get_copy(self, copy_id: int) -> dict[str, Any] | None:
        ...

    def update_copy(self, copy_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        ...

    def copy_exists(self, copy_id: int) -> bool:
        ...

    def copy_has_any_incident(self, copy_id: int) -> bool:
        ...

    def delete_copy_and_incidents(self, copy_id: int) -> bool:
        ...
