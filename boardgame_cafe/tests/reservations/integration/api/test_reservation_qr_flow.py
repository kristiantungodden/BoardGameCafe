from __future__ import annotations

from datetime import datetime

from flask import Flask

import features.reservations.presentation.api.reservation_routes as reservations_module
from features.bookings.domain.models.booking import Booking
from shared.infrastructure.qr_codes import create_reservation_qr_token


def _make_reservation(*, reservation_id: int, customer_id: int, status: str = "confirmed") -> Booking:
    reservation = Booking(
        id=reservation_id,
        customer_id=customer_id,
        start_ts=datetime(2026, 3, 30, 18, 0),
        end_ts=datetime(2026, 3, 30, 20, 0),
        party_size=4,
        status=status,
        notes="Birthday",
    )
    setattr(reservation, "table_id", 2)
    return reservation


class FakeCurrentUser:
    def __init__(self, *, user_id: int, is_authenticated: bool, role: str):
        self.id = user_id
        self.is_authenticated = is_authenticated
        self.role = role


class FakeReservationUseCase:
    def __init__(self, reservation: Booking | None):
        self.reservation = reservation

    def execute(self, reservation_id: int):
        if self.reservation is None or self.reservation.id != reservation_id:
            return None
        return self.reservation


class FakeSeatReservationUseCase:
    def __init__(self):
        self.calls: list[int] = []

    def execute(self, reservation_id: int):
        self.calls.append(reservation_id)
        reservation = _make_reservation(
            reservation_id=reservation_id,
            customer_id=1,
            status="confirmed",
        )
        reservation.seat()
        return reservation


class FakeReservationQrUseCase:
    def __init__(self, secret_key: str):
        self._secret_key = secret_key

    def get_or_create_token(self, secret_key: str, *, user_id: int, reservation_id: int) -> str:
        from shared.infrastructure.qr_codes import create_reservation_qr_token
        return create_reservation_qr_token(secret_key, reservation_id)

    def generate_svg(self, data: str) -> str:
        return "<svg>fake</svg>"


def make_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.register_blueprint(reservations_module.bp)
    return app


def test_reservation_qr_endpoint_returns_svg(monkeypatch):
    app = make_app()
    client = app.test_client()
    reservation = _make_reservation(reservation_id=1, customer_id=7)

    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=7, is_authenticated=True, role="customer"),
    )
    monkeypatch.setattr(
        reservations_module,
        "get_reservation_by_id_use_case",
        lambda: FakeReservationUseCase(reservation),
    )
    monkeypatch.setattr(
        reservations_module,
        "get_reservation_qr_use_case",
        lambda: FakeReservationQrUseCase(app.config["SECRET_KEY"]),
    )

    response = client.get("/api/reservations/1/qr")

    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert response.get_data(as_text=True).lstrip().startswith("<svg")


def test_reservation_qr_endpoint_rejects_other_users(monkeypatch):
    app = make_app()
    client = app.test_client()
    reservation = _make_reservation(reservation_id=1, customer_id=7)

    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=99, is_authenticated=True, role="customer"),
    )
    monkeypatch.setattr(
        reservations_module,
        "get_reservation_by_id_use_case",
        lambda: FakeReservationUseCase(reservation),
    )
    monkeypatch.setattr(
        reservations_module,
        "get_reservation_qr_use_case",
        lambda: FakeReservationQrUseCase(app.config["SECRET_KEY"]),
    )

    response = client.get("/api/reservations/1/qr")

    assert response.status_code == 403
    assert response.get_json()["error"] == "Unauthorized access to reservation"


def test_reservation_checkin_token_seats_reservation_and_redirects(monkeypatch):
    app = make_app()
    client = app.test_client()
    reservation = _make_reservation(reservation_id=1, customer_id=7)
    seat_use_case = FakeSeatReservationUseCase()
    token = create_reservation_qr_token(app.config["SECRET_KEY"], 1)

    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=50, is_authenticated=True, role="staff"),
    )
    monkeypatch.setattr(
        reservations_module,
        "get_reservation_by_id_use_case",
        lambda: FakeReservationUseCase(reservation),
    )
    monkeypatch.setattr(
        reservations_module,
        "get_seat_reservation_use_case",
        lambda: seat_use_case,
    )

    response = client.get(f"/api/reservations/checkin/{token}")

    assert response.status_code == 302
    assert seat_use_case.calls == [1]


def test_reservation_checkin_is_idempotent_when_already_seated(monkeypatch):
    app = make_app()
    client = app.test_client()
    reservation = _make_reservation(reservation_id=1, customer_id=7, status="seated")
    seat_use_case = FakeSeatReservationUseCase()
    token = create_reservation_qr_token(app.config["SECRET_KEY"], 1)

    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=50, is_authenticated=True, role="staff"),
    )
    monkeypatch.setattr(
        reservations_module,
        "get_reservation_by_id_use_case",
        lambda: FakeReservationUseCase(reservation),
    )
    monkeypatch.setattr(
        reservations_module,
        "get_seat_reservation_use_case",
        lambda: seat_use_case,
    )

    response = client.get(f"/api/reservations/checkin/{token}")

    assert response.status_code == 302
    assert seat_use_case.calls == []


def test_reservation_checkin_rejects_unauthenticated_users(monkeypatch):
    app = make_app()
    client = app.test_client()
    token = create_reservation_qr_token(app.config["SECRET_KEY"], 1)

    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=0, is_authenticated=False, role="customer"),
    )

    response = client.get(f"/api/reservations/checkin/{token}")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"