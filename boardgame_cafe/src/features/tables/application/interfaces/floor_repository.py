from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from features.tables.domain.models.floor import Floor


class FloorRepository(ABC):
    @abstractmethod
    def add(self, floor: Floor) -> Floor:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, floor_id: int) -> Optional[Floor]:
        raise NotImplementedError

    @abstractmethod
    def get_by_number(self, floor_number: int) -> Optional[Floor]:
        raise NotImplementedError

    @abstractmethod
    def list(self) -> Sequence[Floor]:
        raise NotImplementedError

    @abstractmethod
    def update(self, floor: Floor) -> Floor:
        raise NotImplementedError

    @abstractmethod
    def delete(self, floor_id: int) -> None:
        raise NotImplementedError