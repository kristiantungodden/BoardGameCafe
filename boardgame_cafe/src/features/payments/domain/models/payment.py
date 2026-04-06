from dataclasses import dataclass

PRICE_PER_CAPACITY_CENTS = 15000  # 150 kr
PRICE_BASE_TABLE = 2500 #25 kr


@dataclass
class Payment:
    table_reservation_id: int
    amount_cents: int
    id: int | None = None
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

    @property
    def amount_kroner(self) -> float:
        return self.amount_cents / 100.0