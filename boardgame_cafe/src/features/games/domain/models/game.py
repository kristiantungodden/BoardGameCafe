from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from decimal import Decimal

if TYPE_CHECKING:
    from features.games.domain.models.game_tag import GameTag


@dataclass
class Game:
    id: Optional[int]
    title: str
    min_players: int
    max_players: int
    playtime_min: int
    complexity: Decimal
    price_cents: int = 0
    description: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[str] = None  # optional, for read-only display
    tags: list["GameTag"] = field(default_factory=list)

    def is_playable_by(self, player_count: int) -> bool:
        """Check if game supports the given number of players."""
        return self.min_players <= player_count <= self.max_players

    def update_details(
        self,
        title: str,
        min_players: int,
        max_players: int,
        playtime_min: int,
        price_cents: int,
        complexity: Decimal,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
    ):
        """Update the game details with validation."""
        if min_players > max_players:
            raise ValueError("min_players cannot be greater than max_players")

        self.title = title
        self.min_players = min_players
        self.max_players = max_players
        self.playtime_min = playtime_min
        self.price_cents = price_cents
        self.complexity = complexity
        self.description = description
        self.image_url = image_url