from datetime import datetime
from pydantic import BaseModel, Field

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