from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class TableAvailabilityQuery(BaseModel):
    start_ts: datetime
    end_ts: datetime
    party_size: int = Field(gt=0)
    floor: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_time_window(self) -> "TableAvailabilityQuery":
        if self.end_ts <= self.start_ts:
            raise ValueError("end_ts must be after start_ts")
        return self