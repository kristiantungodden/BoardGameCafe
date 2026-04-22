from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from shared.domain.exceptions import ValidationError


@dataclass
class Zone:
    floor: int
    name: str
    active: bool = True
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.floor <= 0 or self.floor != int(self.floor):
            raise ValidationError("floor must be a positive integer")
        if not str(self.name).strip():
            raise ValidationError("name is required")
