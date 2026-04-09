from abc import ABC, abstractmethod
from typing import Optional

from features.games.domain.models.game_tag import GameTag
from features.games.domain.models.game_tag_link import GameTagLink


class GameTagRepositoryInterface(ABC):
    @abstractmethod
    def create_tag(self, name: str) -> GameTag:
        pass

    @abstractmethod
    def list_tags(self) -> list[GameTag]:
        pass

    @abstractmethod
    def get_tag_by_id(self, tag_id: int) -> Optional[GameTag]:
        pass

    @abstractmethod
    def attach_tag_to_game(self, game_id: int, tag_id: int) -> GameTagLink:
        pass

    @abstractmethod
    def remove_tag_from_game(self, game_id: int, tag_id: int) -> bool:
        pass

    @abstractmethod
    def list_tags_for_game(self, game_id: int) -> list[GameTag]:
        pass
