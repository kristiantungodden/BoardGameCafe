from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class GameRatingCreateRequest(BaseModel):
    customer_id: int = Field(gt=0)
    game_id: int = Field(gt=0)
    stars: int = Field(ge=1, le=5)
    comment: str | None = None

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class GameRatingResponse(BaseModel):
    id: int | None
    customer_id: int
    game_id: int
    stars: int
    comment: str | None = None
    created_at: datetime | None = None


class GameRatingAverageResponse(BaseModel):
    game_id: int
    average_rating: float | None