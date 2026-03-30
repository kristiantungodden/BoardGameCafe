from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class AvailableTableRepositoryInterface(ABC):
    @abstractmethod
    def get_blocked_table_ids(self, start_ts: datetime, end_ts: datetime) -> set[int]:
        """Get table IDs blocked during the given time window."""
        raise NotImplementedError

    @abstractmethod
    def find_best_available_table(
        self, party_size: int, start_ts: datetime, end_ts: datetime
    ) -> Optional[int]:
        """Find the smallest available table that fits party_size and is not blocked during window."""
        raise NotImplementedError
