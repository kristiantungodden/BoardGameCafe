from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class GameCreated:
    game_id: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GameUpdated:
    game_id: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GameDeleted:
    game_id: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))