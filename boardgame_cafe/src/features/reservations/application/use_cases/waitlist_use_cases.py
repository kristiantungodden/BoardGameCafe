from dataclasses import dataclass
from typing import Sequence

from features.reservations.application.interfaces.waitlist_repository_interface import (
    WaitlistRepositoryInterface,
)
from features.reservations.domain.models.waitlist_entry import WaitlistEntry


@dataclass
class AddToWaitlistCommand:
    customer_id: int
    party_size: int
    notes: str | None = None


class AddToWaitlistUseCase:
    def __init__(self, repo: WaitlistRepositoryInterface):
        self.repo = repo

    def execute(self, cmd: AddToWaitlistCommand) -> WaitlistEntry:
        entry = WaitlistEntry(id=None, customer_id=cmd.customer_id, party_size=cmd.party_size, notes=cmd.notes)
        return self.repo.add(entry)


class ListWaitlistUseCase:
    def __init__(self, repo: WaitlistRepositoryInterface):
        self.repo = repo

    def execute(self) -> Sequence[WaitlistEntry]:
        return list(self.repo.list_all())


class RemoveFromWaitlistUseCase:
    def __init__(self, repo: WaitlistRepositoryInterface):
        self.repo = repo

    def execute(self, entry_id: int) -> bool:
        return self.repo.remove(entry_id)
