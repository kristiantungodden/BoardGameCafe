from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol, Sequence


@dataclass(frozen=True)
class PublicAnnouncement:
    id: int
    title: str
    body: str
    is_published: bool
    published_at: Optional[datetime]
    cta_label: Optional[str]
    cta_url: Optional[str]


class AnnouncementRepositoryInterface(Protocol):
    def list_latest_published(self, limit: int = 5) -> Sequence[PublicAnnouncement]:
        ...
