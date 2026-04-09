from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Sequence

from features.bookings.domain.models.booking import Booking


class BookingRepositoryInterface(ABC):
    @abstractmethod
    def save(self, booking: Booking) -> Booking:
        raise NotImplementedError

    @abstractmethod
    def update(self, booking: Booking) -> Booking:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, booking_id: int) -> Optional[Booking]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, booking_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_by_customer(self, customer_id: int) -> Sequence[Booking]:
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> Sequence[Booking]:
        raise NotImplementedError

    @abstractmethod
    def find_overlapping_bookings(
        self,
        customer_id: int,
        start_ts: datetime,
        end_ts: datetime,
        statuses: set[str],
    ) -> Sequence[Booking]:
        raise NotImplementedError
