from dataclasses import dataclass
from typing import Optional, Sequence

from features.games.application.interfaces.game_copy_repository_interface import GameCopyRepository
from features.games.domain.models.game_copy import GameCopy


@dataclass
class CreateGameCopyCommand:
    game_id: int
    copy_code: str
    status: str = "available"
    location: Optional[str] = None
    condition_note: Optional[str] = None


class CreateGameCopyUseCase:
    def __init__(self, repo: GameCopyRepository):
        self.repo = repo

    def execute(self, cmd: CreateGameCopyCommand) -> GameCopy:
        game_copy = GameCopy(
            game_id=cmd.game_id,
            copy_code=cmd.copy_code,
            status=cmd.status,
            location=cmd.location,
            condition_note=cmd.condition_note,
        )
        return self.repo.add(game_copy)


class ListGameCopiesUseCase:
    def __init__(self, repo: GameCopyRepository):
        self.repo = repo

    def execute(self) -> Sequence[GameCopy]:
        return self.repo.list_all()


class GetGameCopyByIdUseCase:
    def __init__(self, repo: GameCopyRepository):
        self.repo = repo

    def execute(self, copy_id: int) -> Optional[GameCopy]:
        return self.repo.get_by_id(copy_id)


class UpdateGameCopyStatusUseCase:
    def __init__(self, repo: GameCopyRepository):
        self.repo = repo

    def execute(self, copy_id: int, action: str) -> GameCopy:
        game_copy = self.repo.get_by_id(copy_id)

        if not game_copy:
            raise ValueError("Game copy not found")

        if action == "reserve":
            game_copy.reserve()
        elif action == "use":
            game_copy.mark_in_use()
        elif action == "return":
            game_copy.return_to_shelf()
        elif action == "maintenance":
            game_copy.send_to_maintenance()
        elif action == "lost":
            game_copy.mark_lost()
        else:
            raise ValueError("Invalid action")

        return self.repo.update(game_copy)


class UpdateGameCopyLocationUseCase:
    def __init__(self, repo: GameCopyRepository):
        self.repo = repo

    def execute(self, copy_id: int, new_location: str) -> GameCopy:
        game_copy = self.repo.get_by_id(copy_id)

        if not game_copy:
            raise ValueError("Game copy not found")

        game_copy.move(new_location)
        return self.repo.update(game_copy)


class UpdateGameCopyConditionNoteUseCase:
    def __init__(self, repo: GameCopyRepository):
        self.repo = repo

    def execute(self, copy_id: int, note: Optional[str]) -> GameCopy:
        game_copy = self.repo.get_by_id(copy_id)

        if not game_copy:
            raise ValueError("Game copy not found")

        game_copy.update_condition_note(note)
        return self.repo.update(game_copy)