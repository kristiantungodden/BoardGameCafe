from dataclasses import dataclass
from typing import Optional


@dataclass
class GameRating:
    id: Optional[int]
    customer_id: int
    game_id: int
    stars: int
    comment: Optional[str] = None
    created_at: Optional[str] = None

    def validate(self) -> None:
        if not isinstance(self.customer_id, int) or self.customer_id <= 0:
            raise ValueError("customer_id must be a positive integer")

        if not isinstance(self.game_id, int) or self.game_id <= 0:
            raise ValueError("game_id must be a positive integer")

        if not isinstance(self.stars, int) or not (1 <= self.stars <= 5):
            raise ValueError("stars must be an integer between 1 and 5")