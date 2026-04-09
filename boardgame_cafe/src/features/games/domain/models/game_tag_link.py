from dataclasses import dataclass
from typing import Optional

from shared.domain.exceptions import ValidationError


@dataclass
class GameTagLink:
    game_id: int
    game_tag_id: int
    id: Optional[int] = None

    def __post_init__(self) -> None:
        if self.game_id <= 0:
            raise ValidationError("game_id must be a positive integer")
        if self.game_tag_id <= 0:
            raise ValidationError("game_tag_id must be a positive integer")
