import pytest
from flask import Flask

from features.payments.domain.models.payment import Payment
from features.payments.presentation.api import payment_routes
from features.payments.presentation.api.payment_routes import (
    configure_payment_routes,
    payment_bp,
)


class StubRepository:
    def __init__(self):
        self.add_calls = []

    def add(self, payment: Payment) -> Payment:
        self.add_calls.append(payment)
        return Payment(
            id=101,
            table_reservation_id=payment.table_reservation_id,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            status=payment.status,
            provider=payment.provider,
            type=payment.type,
            provider_ref=payment.provider_ref,
        )


def create_test_client(repository=None):
    app = Flask(__name__)
    app.register_blueprint(payment_bp)

    from features.payments.presentation.api import payment_routes
    payment_routes._payment_repository = None
    
    if repository is not None:
        configure_payment_routes(repository)
    return app.test_client()


def test_calculate_payment_route_returns_calculated_values():
    client = create_test_client()

    response = client.post(
        "/payments/calculate",
        json={"table_reservation_id": 3, "party_size": 2},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["table_reservation_id"] == 3
    assert body["party_size"] == 2
    assert body["amount_cents"] == 30000
    assert body["amount_kroner"] == 300.0
    assert body["calculated_amount_cents"] == 30000
    assert body["calculated_amount_kroner"] == 300.0


def test_calculate_payment_route_returns_400_for_invalid_party_size():
    client = create_test_client()

    response = client.post(
        "/payments/calculate",
        json={"table_reservation_id": 3, "party_size": -1},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "party_size cannot be negative"}


def test_create_payment_route_returns_500_when_repository_not_configured():
    client = create_test_client()

    response = client.post(
        "/payments/",
        json={"table_reservation_id": 3, "party_size": 2},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Payment repository is not configured"}


def test_create_payment_route_saves_payment_and_returns_created():
    repository = StubRepository()
    client = create_test_client(repository)

    response = client.post(
        "/payments/",
        json={"table_reservation_id": 4, "party_size": 3},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert len(repository.add_calls) == 1
    assert repository.add_calls[0].table_reservation_id == 4
    assert repository.add_calls[0].amount_cents == 45000
    assert body["id"] == 101
    assert body["amount_cents"] == 45000
    assert body["amount_kroner"] == 450.0


def test_create_payment_route_returns_400_for_missing_reservation_id():
    repository = StubRepository()
    client = create_test_client(repository)

    response = client.post("/payments/", json={"party_size": 2})

    assert response.status_code == 400
    assert response.get_json() == {"error": "table_reservation_id is required"}
