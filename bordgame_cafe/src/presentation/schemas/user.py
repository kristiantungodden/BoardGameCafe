"""Request/Response schemas for the API."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, EmailStr


# User Schemas
class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str = "customer"


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Game Schemas
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


# Game Copy Schemas
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
