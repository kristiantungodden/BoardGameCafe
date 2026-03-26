from dataclasses import dataclass


@dataclass
class Payment:
    table_reservation_id: int
    amount_cents: int
    currency: str = "NOK"
    status: str = "calculated"
    provider: str = "none"
    type: str = "reservation"
    provider_ref: str = "not_created"

    def __post_init__(self) -> None:
        if self.table_reservation_id <= 0:
            raise ValueError("table_reservation_id must be positive")
        if self.amount_cents < 0:
            raise ValueError("amount_cents cannot be negative")