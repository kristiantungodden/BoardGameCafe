"""Schemas package."""

from .user import UserCreate, UserUpdate, UserResponse
from .game import GameCreate, GameUpdate, GameResponse, GameCopyCreate, GameCopyUpdate, GameCopyResponse
from .table import TableCreate, TableUpdate, TableResponse
from .reservation import ReservationCreate, ReservationUpdate, ReservationResponse
from .payment import PaymentCreate, PaymentUpdate, PaymentResponse

__all__ = [
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "GameCreate",
    "GameUpdate",
    "GameResponse",
    "GameCopyCreate",
    "GameCopyUpdate",
    "GameCopyResponse",
    "TableCreate",
    "TableUpdate",
    "TableResponse",
    "ReservationCreate",
    "ReservationUpdate",
    "ReservationResponse",
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentResponse",
]
