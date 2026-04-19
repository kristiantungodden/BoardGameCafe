from dataclasses import dataclass
from typing import Optional, Sequence

from features.games.application.interfaces.game_copy_repository_interface import (
    GameCopyRepository,
)
from features.games.application.interfaces.game_repository_interface import (
    GameRepositoryInterface,
)


@dataclass(frozen=True)
class BrowseGameCopiesQuery:
    game_id: Optional[int] = None
    search_text: str = ""


@dataclass(frozen=True)
class GameCopyBrowseItem:
    id: int
    game_id: int
    game_title: Optional[str]
    copy_code: str
    status: str
    location: Optional[str]
    condition_note: Optional[str]


class BrowseGameCopiesUseCase:
    def __init__(
        self,
        game_copy_repo: GameCopyRepository,
        game_repo: GameRepositoryInterface,
    ):
        self.game_copy_repo = game_copy_repo
        self.game_repo = game_repo

    def execute(self, query: BrowseGameCopiesQuery) -> Sequence[GameCopyBrowseItem]:
        copies = list(self.game_copy_repo.list_all())

        normalized_search = (query.search_text or "").strip().lower()
        if query.game_id is not None:
            copies = [copy for copy in copies if copy.game_id == query.game_id]

        games = self.game_repo.get_all_games()
        title_map = {game.id: game.title for game in games}

        if normalized_search:
            copies = [
                copy
                for copy in copies
                if normalized_search in (copy.copy_code or "").lower()
                or normalized_search in (title_map.get(copy.game_id, "") or "").lower()
            ]

        return [
            GameCopyBrowseItem(
                id=copy.id,
                game_id=copy.game_id,
                game_title=title_map.get(copy.game_id),
                copy_code=copy.copy_code,
                status=copy.status,
                location=copy.location,
                condition_note=copy.condition_note,
            )
            for copy in copies
        ]
