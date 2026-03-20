"""Game and GameCopy domain models."""

from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class GameCopyStatus(str, Enum):
    """Status of a game copy."""
    
    AVAILABLE = "available"
    RESERVED = "reserved"
    CHECKED_OUT = "checked_out"
    MISSING = "missing"
    REPAIR = "repair"


class Game(BaseModel):
    """Game catalogue entry."""
    
    id: Optional[int] = None
    title: str
    description: str
    min_players: int
    max_players: int
    playtime_minutes: int
    complexity_weight: float  # 1-5 scale
    image_url: Optional[str] = None
    tags: List[str] = []
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        return f"{self.title} ({self.min_players}-{self.max_players} players)"


class GameCopy(BaseModel):
    """Physical copy of a game."""
    
    id: Optional[int] = None
    game_id: int
    barcode: Optional[str] = None
    condition: str = "good"  # excellent, good, fair, poor
    status: GameCopyStatus = GameCopyStatus.AVAILABLE
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        return f"Copy {self.id} - Status: {self.status}"
