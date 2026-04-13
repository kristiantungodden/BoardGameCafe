import pytest

from features.games.application.use_cases.game_copy_use_cases import (
    CreateGameCopyCommand,
    CreateGameCopyUseCase,
    GetGameCopyByIdUseCase,
    ListGameCopiesUseCase,
    UpdateGameCopyConditionNoteUseCase,
    UpdateGameCopyLocationUseCase,
    UpdateGameCopyStatusUseCase,
)
from features.games.domain.models.game_copy import GameCopy


class FakeGameCopyRepository:
    def __init__(self):
        self._copies = {}
        self._next_id = 1

    def add(self, game_copy: GameCopy) -> GameCopy:
        persisted = GameCopy(
            id=self._next_id,
            game_id=game_copy.game_id,
            copy_code=game_copy.copy_code,
            status=game_copy.status,
            location=game_copy.location,
            condition_note=game_copy.condition_note,
            updated_at=game_copy.updated_at,
        )
        self._copies[persisted.id] = persisted
        self._next_id += 1
        return persisted

    def get_by_id(self, copy_id: int):
        return self._copies.get(copy_id)

    def list_all(self):
        return list(self._copies.values())

    def update(self, game_copy: GameCopy):
        if game_copy.id not in self._copies:
            raise ValueError("Game copy not found")
        self._copies[game_copy.id] = game_copy
        return game_copy


def _create_game_copy(repo: FakeGameCopyRepository, **overrides) -> GameCopy:
    command = {
        "game_id": 1,
        "copy_code": "CATAN-001",
        "status": "available",
        "location": "Shelf A",
        "condition_note": None,
    }
    command.update(overrides)
    return CreateGameCopyUseCase(repo).execute(CreateGameCopyCommand(**command))


def test_create_game_copy_use_case_persists_copy():
    repo = FakeGameCopyRepository()
    use_case = CreateGameCopyUseCase(repo)

    created = use_case.execute(
        CreateGameCopyCommand(
            game_id=1,
            copy_code="CATAN-001",
            status="available",
            location="Shelf A",
        )
    )

    assert created.id == 1
    assert created.copy_code == "CATAN-001"


def test_list_game_copies_use_case_returns_all_copies():
    repo = FakeGameCopyRepository()
    _create_game_copy(repo, copy_code="CATAN-001")
    _create_game_copy(repo, copy_code="CATAN-002")

    copies = ListGameCopiesUseCase(repo).execute()

    assert len(copies) == 2


def test_get_game_copy_by_id_returns_none_for_missing_copy():
    repo = FakeGameCopyRepository()

    result = GetGameCopyByIdUseCase(repo).execute(999)

    assert result is None


def test_update_status_use_case_applies_actions():
    repo = FakeGameCopyRepository()
    created = _create_game_copy(repo)

    reserved = UpdateGameCopyStatusUseCase(repo).execute(created.id, "reserve")
    assert reserved.status == "reserved"

    in_use = UpdateGameCopyStatusUseCase(repo).execute(created.id, "use")
    assert in_use.status == "in_use"

    returned = UpdateGameCopyStatusUseCase(repo).execute(created.id, "return")
    assert returned.status == "available"

    maintenance = UpdateGameCopyStatusUseCase(repo).execute(created.id, "maintenance")
    assert maintenance.status == "maintenance"


def test_update_status_use_case_rejects_invalid_action():
    repo = FakeGameCopyRepository()
    created = _create_game_copy(repo)

    with pytest.raises(ValueError, match="Invalid action"):
        UpdateGameCopyStatusUseCase(repo).execute(created.id, "repair")


def test_update_status_use_case_rejects_missing_copy():
    repo = FakeGameCopyRepository()

    with pytest.raises(ValueError, match="Game copy not found"):
        UpdateGameCopyStatusUseCase(repo).execute(999, "reserve")


def test_update_location_use_case_updates_location():
    repo = FakeGameCopyRepository()
    created = _create_game_copy(repo)

    updated = UpdateGameCopyLocationUseCase(repo).execute(created.id, "Shelf B")

    assert updated.location == "Shelf B"


def test_update_condition_note_use_case_updates_note():
    repo = FakeGameCopyRepository()
    created = _create_game_copy(repo)

    updated = UpdateGameCopyConditionNoteUseCase(repo).execute(
        created.id, "Corner slightly bent"
    )

    assert updated.condition_note == "Corner slightly bent"
