from datetime import datetime
from pydantic import BaseModel, Field


class ReservationGameSelectionRequest(BaseModel):
    requested_game_id: int = Field(gt=0)
    game_copy_id: int | None = None

class CreateReservationRequest(BaseModel):
    customer_id: int = Field(gt=0)
    table_id: int = Field(gt=0)
    start_ts: datetime
    end_ts: datetime
    party_size: int = Field(gt=0)
    notes: str | None = None

class ReservationResponse(BaseModel):
    id: int | None
    customer_id: int
    table_id: int
    start_ts: datetime
    end_ts: datetime
    party_size: int
    status: str
    notes: str | None = None


class CreateReservationBookingRequest(CreateReservationRequest):
    customer_id: int | None = None
    table_id: int | None = None
    games: list[ReservationGameSelectionRequest] = Field(default_factory=list)