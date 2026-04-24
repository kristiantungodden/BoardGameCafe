from __future__ import annotations

from abc import ABC, abstractmethod


class ReservationQRCodeRepositoryInterface(ABC):
    @abstractmethod
    def delete_for_reservation(self, reservation_id: int) -> None:
        raise NotImplementedError