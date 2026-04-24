from __future__ import annotations

from typing import Sequence

from features.users.application.interfaces.announcement_repository_interface import (
    PublicAnnouncement,
)
from features.users.infrastructure.database.announcement_db import AnnouncementDB
from shared.infrastructure import db


class SqlAlchemyAnnouncementRepository:
    def list_latest_published(self, limit: int = 5) -> Sequence[PublicAnnouncement]:
        rows = (
            db.session.query(AnnouncementDB)
            .filter(AnnouncementDB.is_published.is_(True))
            .order_by(AnnouncementDB.published_at.desc(), AnnouncementDB.id.desc())
            .limit(limit)
            .all()
        )
        return [
            PublicAnnouncement(
                id=row.id,
                title=row.title,
                body=row.body,
                is_published=bool(row.is_published),
                published_at=row.published_at,
                cta_label=row.cta_label,
                cta_url=row.cta_url,
            )
            for row in rows
        ]
