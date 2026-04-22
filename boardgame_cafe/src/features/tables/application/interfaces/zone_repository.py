from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from features.tables.domain.models.zone import Zone


class ZoneRepository(ABC):
    @abstractmethod
    def add(self, zone: Zone) -> Zone:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, zone_id: int) -> Optional[Zone]:
        raise NotImplementedError

    @abstractmethod
    def get_by_floor_and_name(self, floor: int, name: str) -> Optional[Zone]:
        raise NotImplementedError

    @abstractmethod
    def list(self, floor: Optional[int] = None) -> Sequence[Zone]:
        raise NotImplementedError

    @abstractmethod
    def update(self, zone: Zone) -> Zone:
        raise NotImplementedError

    @abstractmethod
    def delete(self, zone_id: int) -> None:
        raise NotImplementedError
