from datetime import datetime, timezone

from features.games.application.use_cases.game_copy_browse_use_cases import (
    BrowseGameCopiesQuery,
    BrowseGameCopiesUseCase,
)
from features.games.domain.models.game import Game
from features.games.domain.models.game_copy import GameCopy


class FakeGameCopyRepository:
    def __init__(self, copies):
        self._copies = list(copies)

    def list_all(self):
        return list(self._copies)


class FakeGameRepository:
    def __init__(self, games):
        self._games = list(games)

    def get_all_games(self):
        return list(self._games)


def test_browse_game_copies_returns_titles_and_all_copies():
    copies = [
        GameCopy(
            id=1,
            game_id=10,
            copy_code="CATAN-001",
            status="available",
            location="Shelf A",
            updated_at=datetime.now(timezone.utc),
        ),
        GameCopy(
            id=2,
            game_id=20,
            copy_code="CHESS-001",
            status="lost",
            location=None,
            updated_at=datetime.now(timezone.utc),
        ),
    ]
    games = [
        Game(id=10, title="Catan", min_players=3, max_players=4, playtime_min=90, complexity=2.5),
        Game(id=20, title="Chess", min_players=2, max_players=2, playtime_min=45, complexity=3.0),
    ]

    use_case = BrowseGameCopiesUseCase(FakeGameCopyRepository(copies), FakeGameRepository(games))

    result = use_case.execute(BrowseGameCopiesQuery())

    assert len(result) == 2
    assert result[0].game_title == "Catan"
    assert result[1].game_title == "Chess"


def test_browse_game_copies_filters_by_game_id_and_search_text():
    copies = [
        GameCopy(
            id=1,
            game_id=10,
            copy_code="CATAN-001",
            status="available",
            updated_at=datetime.now(timezone.utc),
        ),
        GameCopy(
            id=2,
            game_id=10,
            copy_code="CATAN-002",
            status="available",
            updated_at=datetime.now(timezone.utc),
        ),
        GameCopy(
            id=3,
            game_id=20,
            copy_code="CHESS-001",
            status="available",
            updated_at=datetime.now(timezone.utc),
        ),
    ]
    games = [
        Game(id=10, title="Catan", min_players=3, max_players=4, playtime_min=90, complexity=2.5),
        Game(id=20, title="Chess", min_players=2, max_players=2, playtime_min=45, complexity=3.0),
    ]

    use_case = BrowseGameCopiesUseCase(FakeGameCopyRepository(copies), FakeGameRepository(games))

    by_game = use_case.execute(BrowseGameCopiesQuery(game_id=10))
    assert len(by_game) == 2
    assert all(item.game_id == 10 for item in by_game)

    by_search = use_case.execute(BrowseGameCopiesQuery(search_text="CHESS"))
    assert len(by_search) == 1
    assert by_search[0].copy_code == "CHESS-001"
