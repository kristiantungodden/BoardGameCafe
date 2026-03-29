from flask import Flask
import features.reservations.presentation.api.reservation_routes as reservations_module
from features.reservations.domain.models.reservation import TableReservation


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


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(reservations_module.bp)
    return app


def test_post_reservations_creates_reservation(monkeypatch):
    monkeypatch.setattr(
        reservations_module,
        "get_create_reservation_use_case",
        lambda: FakeCreateReservationUseCase(),
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