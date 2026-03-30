from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from features.reservations.domain.models.reservation_game import ReservationGame


class GameReservationRepositoryInterface(ABC):
    @abstractmethod
    def add(self, reservation_game: ReservationGame) -> ReservationGame:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, reservation_game_id: int) -> Optional[ReservationGame]:
        raise NotImplementedError

    @abstractmethod
    def list_for_reservation(self, reservation_id: int) -> Sequence[ReservationGame]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, reservation_game_id: int) -> bool:
        raise NotImplementedError
