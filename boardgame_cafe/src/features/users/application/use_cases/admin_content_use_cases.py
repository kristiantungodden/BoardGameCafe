from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from features.users.application.interfaces.admin_content_port_interface import (
    AdminContentPortInterface,
)


class ContentManagementUseCase:
    def __init__(self, port: AdminContentPortInterface):
        self.port = port

    def list_announcements(self) -> list[dict[str, Any]]:
        return self.port.list_announcements()

    def create_announcement(self, raw: dict[str, Any], creator_id: int | None) -> dict[str, Any]:
        title = str(raw.get("title") or "").strip()
        body = str(raw.get("body") or "").strip()
        if not title:
            raise ValueError("title is required")
        if not body:
            raise ValueError("body is required")

        cta_label = self._parse_optional_text(raw.get("cta_label"))
        cta_url = self._parse_optional_text(raw.get("cta_url"))
        self._validate_announcement_cta(cta_label, cta_url)

        publish_now = bool(raw.get("publish_now", False))

        return self.port.create_announcement(
            {
                "title": title,
                "body": body,
                "cta_label": cta_label,
                "cta_url": cta_url,
                "is_published": publish_now,
                "published_at": datetime.now(timezone.utc) if publish_now else None,
                "created_by": creator_id,
            }
        )

    def update_announcement(self, announcement_id: int, raw: dict[str, Any]) -> dict[str, Any]:
        current = self.port.get_announcement(announcement_id)
        if current is None:
            raise LookupError("Announcement not found")

        if not raw:
            raise ValueError("At least one field must be provided")

        update_payload: dict[str, Any] = {}

        if "title" in raw:
            title = str(raw.get("title") or "").strip()
            if not title:
                raise ValueError("title cannot be blank")
            update_payload["title"] = title

        if "body" in raw:
            body = str(raw.get("body") or "").strip()
            if not body:
                raise ValueError("body cannot be blank")
            update_payload["body"] = body

        if "cta_label" in raw:
            current["cta_label"] = self._parse_optional_text(raw.get("cta_label"))
            update_payload["cta_label"] = current["cta_label"]
        if "cta_url" in raw:
            current["cta_url"] = self._parse_optional_text(raw.get("cta_url"))
            update_payload["cta_url"] = current["cta_url"]

        self._validate_announcement_cta(current.get("cta_label"), current.get("cta_url"))

        updated = self.port.update_announcement(announcement_id, update_payload)
        if updated is None:
            raise LookupError("Announcement not found")
        return updated

    def publish_announcement(self, announcement_id: int) -> dict[str, Any]:
        current = self.port.get_announcement(announcement_id)
        if current is None:
            raise LookupError("Announcement not found")
        if bool(current.get("is_published")):
            raise ValueError("Announcement is already published")

        row = self.port.publish_announcement(announcement_id)
        if row is None:
            raise LookupError("Announcement not found")
        return row

    def unpublish_announcement(self, announcement_id: int) -> dict[str, Any]:
        current = self.port.get_announcement(announcement_id)
        if current is None:
            raise LookupError("Announcement not found")
        if not bool(current.get("is_published")):
            raise ValueError("Announcement is already unpublished")

        row = self.port.unpublish_announcement(announcement_id)
        if row is None:
            raise LookupError("Announcement not found")
        return row

    def delete_announcement(self, announcement_id: int) -> None:
        deleted = self.port.delete_announcement(announcement_id)
        if not deleted:
            raise LookupError("Announcement not found")

    @staticmethod
    def _parse_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text_value = str(value).strip()
        return text_value or None

    @staticmethod
    def _validate_announcement_cta(label: str | None, url: str | None) -> None:
        if bool(label) != bool(url):
            raise ValueError("cta_label and cta_url must either both be set or both be empty")

        if url and not (url.startswith("/") or url.startswith("http://") or url.startswith("https://")):
            raise ValueError("cta_url must start with /, http://, or https://")

