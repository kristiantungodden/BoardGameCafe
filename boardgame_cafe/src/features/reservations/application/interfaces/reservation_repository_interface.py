from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence

from features.bookings.domain.models.booking import Booking


class ReservationRepositoryInterface(ABC):
    @abstractmethod
    def add(self, reservation: Booking) -> Booking:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, reservation_id: int) -> Optional[Booking]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> Sequence[Booking]:
        raise NotImplementedError

    @abstractmethod
    def list_for_table_in_window(
        self, table_id: int, start_ts: datetime, end_ts: datetime
    ) -> Sequence[Booking]:
        raise NotImplementedError

    @abstractmethod
    def update(self, reservation: Booking) -> Booking:
        raise NotImplementedError