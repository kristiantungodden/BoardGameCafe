from pydantic import BaseModel, Field


class AddReservationGameRequest(BaseModel):
    requested_game_id: int = Field(gt=0)
    game_copy_id: int = Field(gt=0)


class ReservationGameResponse(BaseModel):
    id: int | None
    table_reservation_id: int
    requested_game_id: int
    game_copy_id: int
