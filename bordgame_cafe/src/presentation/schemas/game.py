"""Game and GameCopy schemas."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class GameBase(BaseModel):
    """Base game schema."""
    title: str
    description: str
    min_players: int
    max_players: int
    playtime_minutes: int
    complexity_weight: float
    image_url: Optional[str] = None
    tags: List[str] = []


class GameCreate(GameBase):
    """Schema for creating a game."""
    pass


class GameUpdate(BaseModel):
    """Schema for updating a game."""
    title: Optional[str] = None
    description: Optional[str] = None
    min_players: Optional[int] = None
    max_players: Optional[int] = None
    playtime_minutes: Optional[int] = None
    complexity_weight: Optional[float] = None
    image_url: Optional[str] = None
    tags: Optional[List[str]] = None


class GameResponse(GameBase):
    """Schema for game response."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GameCopyBase(BaseModel):
    """Base game copy schema."""
    game_id: int
    barcode: Optional[str] = None
    condition: str = "good"
    status: str = "available"
    notes: Optional[str] = None


class GameCopyCreate(GameCopyBase):
    """Schema for creating a game copy."""
    pass


class GameCopyUpdate(BaseModel):
    """Schema for updating a game copy."""
    condition: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class GameCopyResponse(GameCopyBase):
    """Schema for game copy response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
