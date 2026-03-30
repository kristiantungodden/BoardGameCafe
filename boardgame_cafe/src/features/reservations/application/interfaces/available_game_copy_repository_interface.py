from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class AvailableGameCopyRepositoryInterface(ABC):
    @abstractmethod
    def get_blocked_copy_ids(self, start_ts: datetime, end_ts: datetime) -> set[int]:
        """Get game copy IDs blocked during the given time window."""
        raise NotImplementedError

    @abstractmethod
    def find_available_copy_id(
        self, game_id: int, start_ts: datetime, end_ts: datetime
    ) -> Optional[int]:
        """Find the first available copy for a game that's not blocked during the window."""
        raise NotImplementedError

    @abstractmethod
    def validate_copy_available(
        self, game_copy_id: int, game_id: int, start_ts: datetime, end_ts: datetime
    ) -> bool:
        """Check if a specific copy is available for the game during the window."""
        raise NotImplementedError
