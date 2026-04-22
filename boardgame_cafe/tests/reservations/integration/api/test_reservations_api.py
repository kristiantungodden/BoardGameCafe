from datetime import datetime
from types import SimpleNamespace

import pytest
from flask import Flask
import features.reservations.presentation.api.reservation_routes as reservations_module
from features.bookings.domain.models.booking import Booking
from shared.domain.events import ReservationCancelled
from shared.domain.exceptions import InvalidStatusTransition


def _make_reservation(*, table_id: int, **kwargs) -> Booking:
    reservation = Booking(**kwargs)
    setattr(reservation, "table_id", table_id)
    return reservation


@pytest.fixture(autouse=True)
def _default_authenticated_user():
    reservations_module.current_user = SimpleNamespace(
        id=1,
        is_authenticated=True,
        role="staff",
        is_staff=True,
        is_admin=False,
    )


class FakeTransitionUseCase:
    def __init__(self, status: str):
        self.status = status

    def execute(self, reservation_id: int, actor_user_id=None, actor_role=None):
        if reservation_id != 1:
            return None
        reservation = _make_reservation(
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
    def execute(self, reservation_id: int, actor_user_id=None, actor_role=None):
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
                "booking_id": cmd.reservation_id,
                "requested_game_id": cmd.requested_game_id,
                "game_copy_id": cmd.game_copy_id,
            },
        )()


class FakeRemoveGameFromReservationUseCase:
    def execute(self, reservation_id: int, reservation_game_id: int):
        return reservation_id == 1 and reservation_game_id == 10


class FakeListReservationGamesUseCase:
    def execute(self, reservation_id: int):
        if reservation_id != 1:
            raise InvalidStatusTransition("Reservation not found")
        return [
            type(
                "ReservationGame",
                (),
                {
                    "id": 10,
                    "booking_id": 1,
                    "requested_game_id": 3,
                    "game_copy_id": 7,
                },
            )(),
        ]


class FakeReservationLookupUseCase:
    def execute(self):
        return {
            "tables": [
                {"id": 1, "table_nr": "T1", "capacity": 4, "status": "available"},
            ],
            "games": [
                {"id": 3, "title": "Catan"},
            ],
            "game_copies": [
                {"id": 7, "game_id": 3, "copy_code": "G3-C1", "status": "available"},
            ],
        }


def fake_booking_availability(start_ts, end_ts, party_size):
    return {
        "suggested_table": {
            "id": 2,
            "table_nr": "T2",
            "capacity": 4,
            "status": "available",
        },
        "games": [
            {"id": 3, "title": "Catan", "available": True, "suggested_copy_id": 7},
            {"id": 4, "title": "Chess", "available": False, "suggested_copy_id": None},
        ],
    }


class FakeCurrentUser:
    def __init__(self, user_id: int = 1, is_authenticated: bool = True, is_staff: bool = False):
        self.id = user_id
        self.is_authenticated = is_authenticated
        self.is_staff = is_staff


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(reservations_module.bp)
    return app


def test_post_reservations_creates_booking_with_real_logic(app, test_data):
    """Test booking creation with real auto-table and auto-copy selection logic."""
    user_id = test_data["user"]["id"]
    game_id = test_data["games"][0]["id"]
    table_id = test_data["tables"][0]["id"]

    # Monkeypatch current_user after we have the data
    monkeypatch_user = FakeCurrentUser(user_id=user_id, is_authenticated=True)

    with app.app_context():
        with app.test_client() as client:
            import features.reservations.presentation.api.reservation_routes as reservations_module
            from unittest.mock import patch
            
            with patch.object(reservations_module, 'current_user', monkeypatch_user):
                response = client.post(
                    "/api/reservations",
                    json={
                        "start_ts": "2026-03-30T18:00:00",
                        "end_ts": "2026-03-30T20:00:00",
                        "party_size": 4,
                        "notes": "Birthday",
                        "games": [
                            {"requested_game_id": game_id},
                        ],
                    },
                )

                assert response.status_code == 201
                data = response.get_json()
                assert data["customer_id"] == user_id
                assert data["party_size"] == 4
                assert data["status"] == "created"
                assert len(data["games"]) == 1
                assert data["payment"] is not None
                # Table should be auto-selected (the smallest one fitting the party)
                assert data["table_id"] == table_id
                assert data["table_ids"] == [table_id]


def test_post_reservations_requires_authentication(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=0, is_authenticated=False),
    )

    app = make_app()
    client = app.test_client()

    response = client.post(
        "/api/reservations",
        json={
            "start_ts": "2026-03-30T18:00:00",
            "end_ts": "2026-03-30T20:00:00",
            "party_size": 4,
        },
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_post_reservations_accepts_multiple_selected_tables(app, test_data):
    user_id = test_data["user"]["id"]
    table_ids = [test_data["tables"][0]["id"], test_data["tables"][1]["id"]]

    monkeypatch_user = FakeCurrentUser(user_id=user_id, is_authenticated=True)

    with app.app_context():
        with app.test_client() as client:
            import features.reservations.presentation.api.reservation_routes as reservations_module
            from unittest.mock import patch

            with patch.object(reservations_module, "current_user", monkeypatch_user):
                response = client.post(
                    "/api/reservations",
                    json={
                        "table_id": table_ids[0],
                        "table_ids": table_ids,
                        "start_ts": "2026-03-30T18:00:00",
                        "end_ts": "2026-03-30T20:00:00",
                        "party_size": 1,
                        "games": [],
                    },
                )

                assert response.status_code == 201
                data = response.get_json()
                assert data["table_id"] == table_ids[0]
                assert data["table_ids"] == table_ids


def test_post_reservations_rejects_selected_tables_with_insufficient_combined_capacity(app, test_data):
    user_id = test_data["user"]["id"]
    # table capacities in shared fixture: 4 and 6
    table_ids = [test_data["tables"][0]["id"], test_data["tables"][1]["id"]]

    monkeypatch_user = FakeCurrentUser(user_id=user_id, is_authenticated=True)

    with app.app_context():
        with app.test_client() as client:
            import features.reservations.presentation.api.reservation_routes as reservations_module
            from unittest.mock import patch

            with patch.object(reservations_module, "current_user", monkeypatch_user):
                response = client.post(
                    "/api/reservations",
                    json={
                        "table_id": table_ids[0],
                        "table_ids": table_ids,
                        "start_ts": "2026-03-30T18:00:00",
                        "end_ts": "2026-03-30T20:00:00",
                        "party_size": 11,
                        "games": [],
                    },
                )

                assert response.status_code == 400
                data = response.get_json()
                assert "combined capacity" in data["error"]


def test_get_reservation_availability_returns_suggestions(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_booking_availability_handler",
        lambda: fake_booking_availability,
    )

    app = make_app()
    client = app.test_client()

    response = client.get(
        "/api/reservations/availability?start_ts=2026-03-30T18:00:00&end_ts=2026-03-30T20:00:00&party_size=4"
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["suggested_table"]["id"] == 2
    assert len(data["games"]) == 2
    assert data["games"][0]["available"] is True


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


def test_patch_reservation_cancel_publishes_domain_event(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_cancel_reservation_use_case",
        lambda: FakeTransitionUseCase("cancelled"),
    )

    class FakeEventBus:
        def __init__(self):
            self.events = []

        def publish(self, event):
            self.events.append(event)

    app = make_app()
    app.event_bus = FakeEventBus()
    client = app.test_client()

    response = client.patch("/api/reservations/1/cancel")

    assert response.status_code == 200
    assert len(app.event_bus.events) == 1
    event = app.event_bus.events[0]
    assert isinstance(event, ReservationCancelled)
    assert event.reservation_id == 1
    assert event.cancelled_by_role == "staff"


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
    assert data["booking_id"] == 1
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


def test_get_reservation_games_returns_items(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_list_reservation_games_use_case",
        lambda: FakeListReservationGamesUseCase(),
    )

    app = make_app()
    client = app.test_client()

    response = client.get("/api/reservations/1/games")

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, list)
    assert body[0]["requested_game_id"] == 3


def test_get_reservation_lookup_returns_payload(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_reservation_lookup_use_case",
        lambda: FakeReservationLookupUseCase(),
    )

    app = make_app()
    client = app.test_client()

    response = client.get("/api/reservations/lookup")

    assert response.status_code == 200
    body = response.get_json()
    assert "tables" in body
    assert "games" in body
    assert "game_copies" in body
