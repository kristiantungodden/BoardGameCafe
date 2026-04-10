from abc import ABC, abstractmethod
from typing import Optional, Sequence

from features.games.domain.models.game_copy import GameCopy


class GameCopyRepository(ABC):
    @abstractmethod
    def add(self, game_copy: GameCopy) -> GameCopy:
        pass

    @abstractmethod
    def get_by_id(self, copy_id: int) -> Optional[GameCopy]:
        pass

    @abstractmethod
    def list_all(self) -> Sequence[GameCopy]:
        pass

    @abstractmethod
    def update(self, game_copy: GameCopy) -> GameCopy:
        pass