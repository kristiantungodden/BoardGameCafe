from dataclasses import dataclass
from datetime import datetime


@dataclass
class GameCreated:
    game_id: int
    occurred_at: datetime = datetime.utcnow()


@dataclass
class GameUpdated:
    game_id: int
    occurred_at: datetime = datetime.utcnow()


@dataclass
class GameDeleted:
    game_id: int
    occurred_at: datetime = datetime.utcnow()