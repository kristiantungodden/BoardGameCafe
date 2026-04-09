from dataclasses import dataclass
from typing import Optional

from shared.domain.exceptions import ValidationError


@dataclass
class GameTag:
    id: Optional[int]
    name: str

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError("Tag name cannot be empty")
