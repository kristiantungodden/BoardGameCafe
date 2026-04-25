from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from features.users.infrastructure.database.announcement_db import AnnouncementDB
from shared.infrastructure import db


class SqlAlchemyAdminContentAdapter:
    def list_announcements(self) -> list[dict[str, Any]]:
        rows = (
            db.session.query(AnnouncementDB)
            .order_by(AnnouncementDB.created_at.desc(), AnnouncementDB.id.desc())
            .all()
        )
        return [self._serialize_announcement(row) for row in rows]

    def get_announcement(self, announcement_id: int) -> dict[str, Any] | None:
        row = db.session.get(AnnouncementDB, announcement_id)
        if row is None:
            return None
        return self._serialize_announcement(row)

    def create_announcement(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = AnnouncementDB(**payload)
        db.session.add(row)
        db.session.commit()
        return self._serialize_announcement(row)

    def update_announcement(self, announcement_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        row = db.session.get(AnnouncementDB, announcement_id)
        if row is None:
            return None

        for key, value in payload.items():
            setattr(row, key, value)
        db.session.commit()
        return self._serialize_announcement(row)

    def publish_announcement(self, announcement_id: int) -> dict[str, Any] | None:
        row = db.session.get(AnnouncementDB, announcement_id)
        if row is None:
            return None

        row.is_published = True
        row.published_at = datetime.now(timezone.utc)
        db.session.commit()
        return self._serialize_announcement(row)

    def unpublish_announcement(self, announcement_id: int) -> dict[str, Any] | None:
        row = db.session.get(AnnouncementDB, announcement_id)
        if row is None:
            return None

        row.is_published = False
        db.session.commit()
        return self._serialize_announcement(row)

    def delete_announcement(self, announcement_id: int) -> bool:
        row = db.session.get(AnnouncementDB, announcement_id)
        if row is None:
            return False

        db.session.delete(row)
        db.session.commit()
        return True

    @staticmethod
    def _serialize_announcement(row: AnnouncementDB) -> dict[str, Any]:
        creator = getattr(row, "creator", None)
        return {
            "id": int(row.id),
            "title": row.title,
            "body": row.body,
            "cta_label": row.cta_label,
            "cta_url": row.cta_url,
            "is_published": bool(row.is_published),
            "published_at": row.published_at.isoformat() if getattr(row, "published_at", None) else None,
            "created_at": row.created_at.isoformat() if getattr(row, "created_at", None) else None,
            "updated_at": row.updated_at.isoformat() if getattr(row, "updated_at", None) else None,
            "created_by": int(row.created_by) if row.created_by is not None else None,
            "created_by_name": getattr(creator, "name", None),
        }
