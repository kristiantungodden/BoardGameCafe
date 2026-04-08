from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence


class ReservationLookupRepositoryInterface(ABC):
    @abstractmethod
    def list_tables(self) -> Sequence[dict]:
        raise NotImplementedError

    @abstractmethod
    def list_games(self) -> Sequence[dict]:
        raise NotImplementedError

    @abstractmethod
    def list_game_copies(self) -> Sequence[dict]:
        raise NotImplementedError
