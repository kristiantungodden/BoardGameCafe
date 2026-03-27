from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence

from features.reservations.domain.models.reservation import TableReservation


class ReservationRepositoryInterface(ABC):
    @abstractmethod
    def add(self, reservation: TableReservation) -> TableReservation:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, reservation_id: int) -> Optional[TableReservation]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> Sequence[TableReservation]:
        raise NotImplementedError

    @abstractmethod
    def list_for_table_in_window(
        self, table_id: int, start_ts: datetime, end_ts: datetime
    ) -> Sequence[TableReservation]:
        raise NotImplementedError

    @abstractmethod
    def update(self, reservation: TableReservation) -> TableReservation:
        raise NotImplementedError