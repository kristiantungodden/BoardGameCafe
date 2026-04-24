from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from features.bookings.domain.models.booking_status_history import (
    BookingStatusHistoryEntry,
)


class BookingStatusHistoryRepositoryInterface(ABC):
    @abstractmethod
    def save(self, entry: BookingStatusHistoryEntry) -> BookingStatusHistoryEntry:
        raise NotImplementedError

    @abstractmethod
    def list_for_booking(self, booking_id: int) -> Sequence[BookingStatusHistoryEntry]:
        raise NotImplementedError

    @abstractmethod
    def delete_for_booking(self, booking_id: int) -> None:
        raise NotImplementedError
