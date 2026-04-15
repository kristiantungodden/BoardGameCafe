from __future__ import annotations
 
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
 
from shared.domain.exceptions import ValidationError
 
 
VALID_INCIDENT_TYPES = {"damage", "loss"}
 
 
@dataclass
class Incident:
    """Domain entity representing a damage or loss report for a game copy."""
 
    game_copy_id: int
    reported_by: int          # steward user id
    incident_type: str        # "damage" or "loss"
    note: str
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
 
    def __post_init__(self) -> None:
        self._validate()
 
    def _validate(self) -> None:
        if self.game_copy_id <= 0:
            raise ValidationError("game_copy_id must be a positive integer")
        if self.reported_by <= 0:
            raise ValidationError("reported_by must be a positive integer")
        if self.incident_type not in VALID_INCIDENT_TYPES:
            raise ValidationError(
                f"incident_type must be one of: {', '.join(sorted(VALID_INCIDENT_TYPES))}"
            )
        if not self.note or not self.note.strip():
            raise ValidationError("note cannot be empty")