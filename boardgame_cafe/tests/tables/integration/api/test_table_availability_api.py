from datetime import datetime

from flask import Flask

import features.tables.presentation.api.table_routes as table_routes


class FakeTableAvailabilityUseCase:
    def execute(self, start_ts, end_ts, party_size, floor=None):
        return {
            "filters": {
                "start_ts": start_ts.isoformat(),
                "end_ts": end_ts.isoformat(),
                "party_size": party_size,
                "floor": floor,
            },
            "floors": [
                {
                    "floor": 2,
                    "zones": [
                        {
                            "zone": "B",
                            "tables": [
                                {
                                    "id": 4,
                                    "table_nr": "4",
                                    "capacity": 6,
                                    "floor": 2,
                                    "zone": "B",
                                    "status": "available",
                                    "available": True,
                                    "unavailable_reasons": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        }


def make_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(table_routes.bp)
    return app


def test_get_table_availability_returns_grouped_payload(monkeypatch):
    monkeypatch.setattr(
        table_routes,
        "get_table_availability_use_case",
        lambda: FakeTableAvailabilityUseCase(),
    )

    app = make_app()
    client = app.test_client()

    response = client.get(
        "/api/tables/availability?start_ts=2026-04-10T18:00:00&end_ts=2026-04-10T20:00:00&party_size=4&floor=2"
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["filters"]["floor"] == 2
    assert body["floors"][0]["floor"] == 2
    assert body["floors"][0]["zones"][0]["zone"] == "B"


def test_get_table_availability_rejects_invalid_query(monkeypatch):
    monkeypatch.setattr(
        table_routes,
        "get_table_availability_use_case",
        lambda: FakeTableAvailabilityUseCase(),
    )

    app = make_app()
    client = app.test_client()

    response = client.get(
        "/api/tables/availability?start_ts=2026-04-10T20:00:00&end_ts=2026-04-10T18:00:00&party_size=4"
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Validation failed"