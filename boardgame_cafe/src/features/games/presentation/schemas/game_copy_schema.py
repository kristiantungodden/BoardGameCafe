from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


VALID_GAME_COPY_STATUSES = {"available", "reserved", "in_use", "maintenance"}
VALID_GAME_COPY_ACTIONS = {"reserve", "use", "return", "maintenance"}


class GameCopyCreateRequest(BaseModel):
    game_id: int = Field(gt=0)
    copy_code: str = Field(min_length=1)
    status: str = "available"
    location: str | None = None
    condition_note: str | None = None

    @field_validator("copy_code")
    @classmethod
    def validate_copy_code(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("copy_code cannot be empty")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_GAME_COPY_STATUSES:
            raise ValueError(
                f"status must be one of: {', '.join(sorted(VALID_GAME_COPY_STATUSES))}"
            )
        return value

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("condition_note")
    @classmethod
    def validate_condition_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class GameCopyStatusUpdateRequest(BaseModel):
    action: str = Field(min_length=1)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        value = value.strip()
        if value not in VALID_GAME_COPY_ACTIONS:
            raise ValueError(
                "action must be one of: reserve, use, return, maintenance"
            )
        return value


class GameCopyLocationUpdateRequest(BaseModel):
    location: str = Field(min_length=1)

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("location cannot be empty")
        return value


class GameCopyConditionNoteUpdateRequest(BaseModel):
    condition_note: str | None = None

    @field_validator("condition_note")
    @classmethod
    def validate_condition_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class GameCopyResponse(BaseModel):
    id: int | None
    game_id: int
    copy_code: str
    status: str
    location: str | None = None
    condition_note: str | None = None
    updated_at: datetime | None = None