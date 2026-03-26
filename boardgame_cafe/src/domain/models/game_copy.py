from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from domain.exceptions import InvalidStatusTransition, ValidationError


VALID_GAME_COPY_STATUSES = {"available", "reserved", "in_use", "maintenance"}


@dataclass
class GameCopy:
    """Domain entity for a physical copy of a board game."""

    game_id: int
    copy_code: str
    status: str = "available"
    location: Optional[str] = None
    condition_note: Optional[str] = None
    id: Optional[int] = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.game_id <= 0:
            raise ValidationError("game_id must be a positive integer")

        if not self.copy_code or not self.copy_code.strip():
            raise ValidationError("copy_code cannot be empty")

        if self.status not in VALID_GAME_COPY_STATUSES:
            raise ValidationError(
                f"status must be one of: {', '.join(sorted(VALID_GAME_COPY_STATUSES))}"
            )

    def is_available(self) -> bool:
        return self.status == "available"

    def reserve(self) -> None:
        if self.status != "available":
            raise InvalidStatusTransition(
                f"Cannot reserve game copy in status '{self.status}'"
            )
        self.status = "reserved"
        self.updated_at = datetime.utcnow()

    def mark_in_use(self) -> None:
        if self.status not in {"available", "reserved"}:
            raise InvalidStatusTransition(
                f"Cannot mark game copy as in use from status '{self.status}'"
            )
        self.status = "in_use"
        self.updated_at = datetime.utcnow()

    def return_to_shelf(self, location: Optional[str] = None) -> None:
        self.status = "available"
        if location is not None and location.strip():
            self.location = location
        self.updated_at = datetime.utcnow()

    def send_to_maintenance(self) -> None:
        if self.status == "maintenance":
            raise InvalidStatusTransition("Game copy is already in maintenance")
        self.status = "maintenance"
        self.updated_at = datetime.utcnow()

    def update_condition_note(self, note: Optional[str]) -> None:
        self.condition_note = note
        self.updated_at = datetime.utcnow()

    def move(self, new_location: str) -> None:
        if not new_location or not new_location.strip():
            raise ValidationError("new_location cannot be empty")
        self.location = new_location
        self.updated_at = datetime.utcnow()