from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class GameBaseRequest(BaseModel):
	title: str = Field(min_length=1)
	min_players: int = Field(gt=0)
	max_players: int = Field(gt=0)
	playtime_min: int = Field(gt=0)
	complexity: Decimal = Field(ge=0)
	description: str | None = None
	image_url: str | None = None

	@field_validator("title")
	@classmethod
	def validate_title(cls, value: str) -> str:
		title = value.strip()
		if not title:
			raise ValueError("title cannot be empty")
		return title

	@model_validator(mode="after")
	def validate_player_range(self):
		if self.min_players > self.max_players:
			raise ValueError("min_players cannot be greater than max_players")
		return self


class GameCreateRequest(GameBaseRequest):
	pass


class GameUpdateRequest(BaseModel):
	title: str | None = Field(default=None, min_length=1)
	min_players: int | None = Field(default=None, gt=0)
	max_players: int | None = Field(default=None, gt=0)
	playtime_min: int | None = Field(default=None, gt=0)
	complexity: Decimal | None = Field(default=None, ge=0)
	description: str | None = None
	image_url: str | None = None

	@field_validator("title")
	@classmethod
	def validate_title(cls, value: str | None) -> str | None:
		if value is None:
			return None
		title = value.strip()
		if not title:
			raise ValueError("title cannot be empty")
		return title

	@model_validator(mode="after")
	def validate_player_range(self):
		if (
			self.min_players is not None
			and self.max_players is not None
			and self.min_players > self.max_players
		):
			raise ValueError("min_players cannot be greater than max_players")
		return self


class GameResponse(BaseModel):
	id: int | None
	title: str
	min_players: int
	max_players: int
	playtime_min: int
	complexity: float
	description: str | None = None
	image_url: str | None = None
	created_at: datetime | None = None


class GameTagCreateRequest(BaseModel):
	name: str = Field(min_length=1)

	@field_validator("name")
	@classmethod
	def validate_name(cls, value: str) -> str:
		name = value.strip()
		if not name:
			raise ValueError("Tag name cannot be empty")
		return name


class GameTagResponse(BaseModel):
	id: int
	name: str


class GameTagLinkCreateRequest(BaseModel):
	tag_id: int = Field(gt=0)


class GameTagLinkResponse(BaseModel):
	id: int
	game_id: int
	game_tag_id: int
