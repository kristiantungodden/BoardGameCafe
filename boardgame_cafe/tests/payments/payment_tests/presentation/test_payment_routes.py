import pytest
from flask import Flask
from types import SimpleNamespace

from features.payments.domain.models.payment import Payment
from features.payments.presentation.api import payment_routes
from features.payments.presentation.api.payment_routes import (
    configure_booking_repository,
    configure_payment_provider,
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
            booking_id=payment.booking_id,
            amount_cents=payment.amount_cents,
            currency=payment.currency,
            status=payment.status,
            provider=payment.provider,
            type=payment.type,
            provider_ref=payment.provider_ref,
        )


class StubBookingRepository:
    def get_by_id(self, booking_id: int):
        return SimpleNamespace(id=booking_id, customer_id=1)


class StubProvider:
    def start_payment(self, payment):
        return SimpleNamespace(
            provider_ref="cs_test",
            redirect_url="https://stripe.example/checkout",
            provider_name="stripe",
        )

    def fetch_status(self, provider_ref: str):
        return "pending"

    def refund(self, provider_ref: str) -> bool:
        return True


def create_test_client(repository=None):
    app = Flask(__name__)
    app.register_blueprint(payment_bp)

    from features.payments.presentation.api import payment_routes
    payment_routes._payment_service = None
    payment_routes._pending_repository = None
    payment_routes._pending_provider = None
    payment_routes._pending_booking_repository = None
    payment_routes.current_user = SimpleNamespace(
        id=1,
        is_authenticated=True,
        role="admin",
        is_staff=True,
        is_admin=True,
    )
    configure_booking_repository(StubBookingRepository())
    configure_payment_provider(StubProvider())
    
    if repository is not None:
        configure_payment_routes(repository)
    return app.test_client()


def test_calculate_payment_route_returns_calculated_values():
    client = create_test_client(StubRepository())

    response = client.post(
        "/api/payments/calculate",
        json={"booking_id": 3, "party_size": 2},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["booking_id"] == 3
    assert body["party_size"] == 2
    assert body["amount_cents"] == 32500
    assert body["amount_kroner"] == 325.0
    assert body["calculated_amount_cents"] == 32500
    assert body["calculated_amount_kroner"] == 325.0


def test_calculate_payment_route_returns_400_for_invalid_party_size():
    client = create_test_client(StubRepository())

    response = client.post(
        "/api/payments/calculate",
        json={"booking_id": 3, "party_size": -1},
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "party_size must be at least 1"}


def test_create_payment_route_returns_500_when_repository_not_configured():
    client = create_test_client()

    response = client.post(
        "/api/payments/",
        json={"booking_id": 3, "party_size": 2},
    )

    assert response.status_code == 500
    assert response.get_json() == {"error": "Payment service is not configured"}


def test_create_payment_route_saves_payment_and_returns_created():
    repository = StubRepository()
    client = create_test_client(repository)

    response = client.post(
        "/api/payments/",
        json={"booking_id": 4, "party_size": 3},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert len(repository.add_calls) == 1
    assert repository.add_calls[0].booking_id == 4
    assert repository.add_calls[0].amount_cents == 47500
    assert body["id"] == 101
    assert body["amount_cents"] == 47500
    assert body["amount_kroner"] == 475.0


def test_create_payment_route_returns_400_for_missing_reservation_id():
    repository = StubRepository()
    client = create_test_client(repository)

    response = client.post("/api/payments/", json={"party_size": 2})

    assert response.status_code == 400
    assert response.get_json() == {"error": "booking_id is required"}
