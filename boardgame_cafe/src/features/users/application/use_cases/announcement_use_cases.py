from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from features.users.application.interfaces.announcement_repository_interface import (
    AnnouncementRepositoryInterface,
    PublicAnnouncement,
)


@dataclass(frozen=True)
class ListLatestPublishedAnnouncementsQuery:
    limit: int = 5


class ListLatestPublishedAnnouncementsUseCase:
    def __init__(self, repository: AnnouncementRepositoryInterface):
        self.repository = repository

    def execute(self, query: ListLatestPublishedAnnouncementsQuery) -> Sequence[PublicAnnouncement]:
        return self.repository.list_latest_published(limit=query.limit)
