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

        return {"table_reservation_id": reservation_id}

    @staticmethod
    def dump(payment: Payment) -> dict[str, Any]:
        return {
            "id": payment.id,
            "table_reservation_id": payment.table_reservation_id,
            "amount_cents": payment.amount_cents,
            "amount_kroner": payment.amount_kroner,
            "currency": payment.currency,
            "status": payment.status,
            "provider": payment.provider,
            "type": payment.type,
            "provider_ref": payment.provider_ref,
        }

    @classmethod
    def dump_many(cls, payments: list[Payment]) -> list[dict[str, Any]]:
        return [cls.dump(payment) for payment in payments]
