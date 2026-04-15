from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from features.reservations.domain.models.waitlist_entry import WaitlistEntry


class WaitlistRepositoryInterface(ABC):
    @abstractmethod
    def add(self, entry: WaitlistEntry) -> WaitlistEntry:
        raise NotImplementedError()

    @abstractmethod
    def list_all(self) -> Sequence[WaitlistEntry]:
        raise NotImplementedError()

    @abstractmethod
    def remove(self, entry_id: int) -> bool:
        raise NotImplementedError()
