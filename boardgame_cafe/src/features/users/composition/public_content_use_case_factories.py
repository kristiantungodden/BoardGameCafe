from __future__ import annotations

from features.users.application.use_cases.announcement_use_cases import (
    ListLatestPublishedAnnouncementsQuery,
    ListLatestPublishedAnnouncementsUseCase,
)
from features.users.infrastructure.repositories.announcement_repository import (
    SqlAlchemyAnnouncementRepository,
)

_announcement_repo = SqlAlchemyAnnouncementRepository()


def get_list_latest_published_announcements_handler():
    def _list_latest(limit: int = 5):
        use_case = ListLatestPublishedAnnouncementsUseCase(_announcement_repo)
        return use_case.execute(ListLatestPublishedAnnouncementsQuery(limit=limit))

    return _list_latest
