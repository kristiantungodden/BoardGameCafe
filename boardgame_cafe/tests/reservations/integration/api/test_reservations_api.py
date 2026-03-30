from datetime import datetime

from flask import Flask
import features.reservations.presentation.api.reservation_routes as reservations_module
from features.reservations.domain.models.reservation import TableReservation
from features.payments.domain.models.payment import Payment
from shared.domain.exceptions import InvalidStatusTransition


class FakeCreateReservationUseCase:
    def execute(self, cmd):
        return TableReservation(
            id=1,
            customer_id=cmd.customer_id,
            table_id=cmd.table_id,
            start_ts=cmd.start_ts,
            end_ts=cmd.end_ts,
            party_size=cmd.party_size,
            notes=cmd.notes,
        )


def fake_create_with_payment(cmd):
    reservation = TableReservation(
        id=1,
        customer_id=cmd.customer_id,
        table_id=cmd.table_id,
        start_ts=cmd.start_ts,
        end_ts=cmd.end_ts,
        party_size=cmd.party_size,
        notes=cmd.notes,
    )
    payment = Payment(
        id=101,
        table_reservation_id=reservation.id,
        amount_cents=reservation.party_size * 15000,
    )
    return reservation, payment


class FakeTransitionUseCase:
    def __init__(self, status: str):
        self.status = status

    def execute(self, reservation_id: int):
        if reservation_id != 1:
            return None
        reservation = TableReservation(
            id=1,
            customer_id=1,
            table_id=2,
            start_ts=datetime(2026, 3, 30, 18, 0),
            end_ts=datetime(2026, 3, 30, 20, 0),
            party_size=4,
            notes="Bursdag",
            status=self.status,
        )
        return reservation


class FailingTransitionUseCase:
    def execute(self, reservation_id: int):
        raise InvalidStatusTransition("Cannot complete reservation in status 'confirmed'")


class FakeAddGameToReservationUseCase:
    def execute(self, cmd):
        if cmd.reservation_id != 1:
            raise InvalidStatusTransition("Reservation not found")
        return type(
            "ReservationGame",
            (),
            {
                "id": 10,
                "table_reservation_id": cmd.reservation_id,
                "requested_game_id": cmd.requested_game_id,
                "game_copy_id": cmd.game_copy_id,
            },
        )()


class FakeRemoveGameFromReservationUseCase:
    def execute(self, reservation_id: int, reservation_game_id: int):
        return reservation_id == 1 and reservation_game_id == 10


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(reservations_module.bp)
    return app


def test_post_reservations_creates_reservation(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_create_reservation_with_payment_handler",
        lambda: fake_create_with_payment,
    )

    app = make_app()
    client = app.test_client()

    response = client.post(
        "/api/reservations",
        json={
            "customer_id": 1,
            "table_id": 2,
            "start_ts": "2026-03-30T18:00:00",
            "end_ts": "2026-03-30T20:00:00",
            "party_size": 4,
            "notes": "Bursdag",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] == 1
    assert data["party_size"] == 4
    assert data["status"] == "confirmed"
    assert data["payment"]["table_reservation_id"] == 1
    assert data["payment"]["amount_cents"] == 60000


def test_patch_reservation_cancel_updates_status(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_cancel_reservation_use_case",
        lambda: FakeTransitionUseCase("cancelled"),
    )

    app = make_app()
    client = app.test_client()

    response = client.patch("/api/reservations/1/cancel")

    assert response.status_code == 200
    assert response.get_json()["status"] == "cancelled"


def test_patch_reservation_seat_not_found(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_seat_reservation_use_case",
        lambda: FakeTransitionUseCase("seated"),
    )

    app = make_app()
    client = app.test_client()

    response = client.patch("/api/reservations/999/seat")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Reservation not found"


def test_patch_reservation_complete_invalid_transition(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_complete_reservation_use_case",
        lambda: FailingTransitionUseCase(),
    )

    app = make_app()
    client = app.test_client()

    response = client.patch("/api/reservations/1/complete")

    assert response.status_code == 400
    assert "Cannot complete reservation" in response.get_json()["error"]


def test_patch_reservation_no_show_updates_status(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_no_show_reservation_use_case",
        lambda: FakeTransitionUseCase("no_show"),
    )

    app = make_app()
    client = app.test_client()

    response = client.patch("/api/reservations/1/no-show")

    assert response.status_code == 200
    assert response.get_json()["status"] == "no_show"


def test_post_reservation_games_adds_game_to_booking(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_add_game_to_reservation_use_case",
        lambda: FakeAddGameToReservationUseCase(),
    )

    app = make_app()
    client = app.test_client()

    response = client.post(
        "/api/reservations/1/games",
        json={"requested_game_id": 3, "game_copy_id": 7},
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["table_reservation_id"] == 1
    assert data["requested_game_id"] == 3
    assert data["game_copy_id"] == 7


def test_delete_reservation_game_removes_game_from_booking(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_remove_game_from_reservation_use_case",
        lambda: FakeRemoveGameFromReservationUseCase(),
    )

    app = make_app()
    client = app.test_client()

    response = client.delete("/api/reservations/1/games/10")

    assert response.status_code == 204


def test_delete_reservation_game_not_found(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_remove_game_from_reservation_use_case",
        lambda: FakeRemoveGameFromReservationUseCase(),
    )

    app = make_app()
    client = app.test_client()

    response = client.delete("/api/reservations/1/games/999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Reservation game not found"