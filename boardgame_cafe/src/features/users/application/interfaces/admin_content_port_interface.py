from __future__ import annotations

from typing import Any, Protocol


class AdminContentPortInterface(Protocol):
    def list_announcements(self) -> list[dict[str, Any]]:
        ...

    def get_announcement(self, announcement_id: int) -> dict[str, Any] | None:
        ...

    def create_announcement(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def update_announcement(self, announcement_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        ...

    def publish_announcement(self, announcement_id: int) -> dict[str, Any] | None:
        ...

    def unpublish_announcement(self, announcement_id: int) -> dict[str, Any] | None:
        ...

    def delete_announcement(self, announcement_id: int) -> bool:
        ...
