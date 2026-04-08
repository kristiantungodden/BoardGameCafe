from typing import Any

from features.payments.domain.models.payment import Payment


class PaymentSchema:
    @staticmethod
    def validate_create_request(data: dict[str, Any]) -> dict[str, int]:
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")

        reservation_id = data.get("table_reservation_id")
        if reservation_id is None:
            raise ValueError("table_reservation_id is required")
        if not isinstance(reservation_id, int):
            raise ValueError("table_reservation_id must be an integer")
        if reservation_id <= 0:
            raise ValueError("table_reservation_id must be positive")
        
        party_size = data.get("party_size")
        if party_size is None:
            raise ValueError("party_size is required")
        if not isinstance(party_size, int):
            raise ValueError("party_size must be an integer")
        if party_size <= 0:
            raise ValueError("party_size must be at least 1")

        return {"table_reservation_id": reservation_id, "party_size": party_size}

    @staticmethod
    def dump(payment: Payment) -> dict[str, Any]:
        return {
            "id": payment.id,
            "table_reservation_id": payment.table_reservation_id,
            "amount_cents": payment.amount_cents,
            "amount_kroner": payment.amount_kroner,
            "currency": payment.currency,
            "status": payment.status.value,
            "provider": payment.provider,
            "type": payment.type,
            "provider_ref": payment.provider_ref,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
            }

    @classmethod
    def dump_many(cls, payments: list[Payment]) -> list[dict[str, Any]]:
        return [cls.dump(payment) for payment in payments]
