from dataclasses import dataclass

from features.games.application.interfaces.game_tag_repository_interface import (
    GameTagRepositoryInterface,
)
from features.games.domain.models.game_tag import GameTag
from features.games.domain.models.game_tag_link import GameTagLink


@dataclass
class CreateGameTagCommand:
    name: str


@dataclass
class AttachGameTagCommand:
    game_id: int
    tag_id: int


class CreateGameTagUseCase:
    def __init__(self, repository: GameTagRepositoryInterface):
        self.repository = repository

    def execute(self, cmd: CreateGameTagCommand) -> GameTag:
        return self.repository.create_tag(cmd.name)


class ListGameTagsUseCase:
    def __init__(self, repository: GameTagRepositoryInterface):
        self.repository = repository

    def execute(self) -> list[GameTag]:
        return self.repository.list_tags()


class AttachGameTagUseCase:
    def __init__(self, repository: GameTagRepositoryInterface):
        self.repository = repository

    def execute(self, cmd: AttachGameTagCommand) -> GameTagLink:
        return self.repository.attach_tag_to_game(cmd.game_id, cmd.tag_id)


class RemoveGameTagUseCase:
    def __init__(self, repository: GameTagRepositoryInterface):
        self.repository = repository

    def execute(self, game_id: int, tag_id: int) -> bool:
        return self.repository.remove_tag_from_game(game_id, tag_id)


class ListGameTagsForGameUseCase:
    def __init__(self, repository: GameTagRepositoryInterface):
        self.repository = repository

    def execute(self, game_id: int) -> list[GameTag]:
        return self.repository.list_tags_for_game(game_id)
