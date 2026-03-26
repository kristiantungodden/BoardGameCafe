from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence

from domain.models.table import Table


@dataclass(frozen=True)
class TableFilters:
    zone: Optional[str] = None
    status: Optional[str] = None
    min_capacity: Optional[int] = None
    max_capacity: Optional[int] = None
    feature: Optional[str] = None
    is_available: Optional[bool] = None


class TableRepository(ABC):
    @abstractmethod
    def add(self, table: Table) -> Table:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, table_id: int) -> Optional[Table]:
        raise NotImplementedError

    @abstractmethod
    def list(self) -> Sequence[Table]:
        raise NotImplementedError

    @abstractmethod
    def update(self, table: Table) -> Table:
        raise NotImplementedError

    @abstractmethod
    def delete(self, table_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, filters: Optional[TableFilters] = None) -> Sequence[Table]:
        raise NotImplementedError

    @abstractmethod
    def count_by_status(self) -> dict[str, int]:
        raise NotImplementedError
