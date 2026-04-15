"""
Integration tests for reservation draft endpoints.
Tests server-side ephemeral persistence of booking progress.
"""

import features.reservations.presentation.api.reservation_routes as reservations_module


class FakeCurrentUser:
    """Mock current_user for testing."""
    def __init__(self, *, user_id: int, is_authenticated: bool):
        self.id = user_id
        self.is_authenticated = is_authenticated


def test_get_empty_draft_when_not_authenticated(client, monkeypatch):
    """Anonymous users cannot access draft endpoints."""
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=0, is_authenticated=False),
    )
    response = client.get("/api/reservations/draft")
    assert response.status_code == 401
    assert response.json["error"] == "Authentication required"


def test_save_draft_requires_authentication(client, monkeypatch):
    """Anonymous users cannot save drafts."""
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=0, is_authenticated=False),
    )
    response = client.post(
        "/api/reservations/draft-save",
        json={"party_size": 2},
    )
    assert response.status_code == 401


def test_get_empty_draft_on_first_access(client, monkeypatch):
    """First access returns empty draft object."""
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=1, is_authenticated=True),
    )
    response = client.get("/api/reservations/draft")
    assert response.status_code == 200
    assert response.json == {}


def test_save_and_retrieve_draft(client, monkeypatch):
    """Saving a draft persists it in session and can be retrieved."""
    draft_data = {
        "party_size": 4,
        "table_ids": [1, 2],
        "table_id": 1,
        "start_ts": "2026-04-20T18:00:00",
        "end_ts": "2026-04-20T20:00:00",
        "notes": "High-top table preferred",
        "games": [
            {"requested_game_id": 1, "game_copy_id": None},
            {"requested_game_id": 2, "game_copy_id": 5},
        ],
    }
    
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=5, is_authenticated=True),
    )

    # Save draft
    save_response = client.post("/api/reservations/draft-save", json=draft_data)
    assert save_response.status_code == 200
    assert save_response.json["saved"] is True
    saved_draft = save_response.json["draft"]

    # Verify draft contains expected fields
    assert saved_draft["party_size"] == draft_data["party_size"]
    assert saved_draft["table_ids"] == draft_data["table_ids"]
    assert saved_draft["start_ts"] == draft_data["start_ts"]
    assert saved_draft["end_ts"] == draft_data["end_ts"]
    assert saved_draft["notes"] == draft_data["notes"]
    assert saved_draft["games"] == draft_data["games"]

    # Retrieve draft
    get_response = client.get("/api/reservations/draft")
    assert get_response.status_code == 200
    retrieved_draft = get_response.json

    # Verify retrieved draft matches saved draft
    assert retrieved_draft["party_size"] == draft_data["party_size"]
    assert retrieved_draft["table_ids"] == draft_data["table_ids"]
    assert retrieved_draft["games"] == draft_data["games"]


def test_partial_draft_update(client, monkeypatch):
    """Partial draft updates are supported."""
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=2, is_authenticated=True),
    )

    # Save initial draft with full data
    initial_draft = {
        "party_size": 4,
        "table_ids": [1, 2],
        "start_ts": "2026-04-20T18:00:00",
        "notes": "Initial notes",
        "games": [],
    }
    client.post("/api/reservations/draft-save", json=initial_draft)

    # Update only party_size
    partial_update = {"party_size": 6}
    update_response = client.post("/api/reservations/draft-save", json=partial_update)
    assert update_response.status_code == 200

    # Verify the draft was updated
    get_response = client.get("/api/reservations/draft")
    retrieved = get_response.json
    assert retrieved["party_size"] == 6
    # Other fields from partial update should still be present
    assert retrieved["start_ts"] == initial_draft["start_ts"]


def test_draft_persists_across_requests(client, monkeypatch):
    """Draft persists in session across multiple requests."""
    draft_data = {
        "party_size": 4,
        "table_ids": [1, 2],
        "start_ts": "2026-04-20T18:00:00",
        "end_ts": "2026-04-20T20:00:00",
        "games": [],
    }
    
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=3, is_authenticated=True),
    )

    # Save draft
    client.post("/api/reservations/draft-save", json=draft_data)

    # Retrieve draft multiple times
    for _ in range(3):
        response = client.get("/api/reservations/draft")
        assert response.status_code == 200
        assert response.json["party_size"] == draft_data["party_size"]


def test_clear_draft_by_posting_empty(client, monkeypatch):
    """Draft can be cleared by posting empty object."""
    draft_data = {
        "party_size": 4,
        "table_ids": [1, 2],
        "games": [],
    }
    
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=4, is_authenticated=True),
    )

    # Save draft
    client.post("/api/reservations/draft-save", json=draft_data)

    # Verify draft exists
    get_response = client.get("/api/reservations/draft")
    assert get_response.json["party_size"] == draft_data["party_size"]

    # Clear draft
    clear_response = client.post("/api/reservations/draft-save", json={})
    assert clear_response.status_code == 200
    assert clear_response.json["draft"] == {}

    # Verify draft is mostly empty (only user_id remains)
    get_response = client.get("/api/reservations/draft")
    retrieved = get_response.json
    assert "party_size" not in retrieved or retrieved.get("party_size") is None


def test_draft_includes_user_id(client, monkeypatch):
    """Saving a draft does not leak user identity into the payload."""
    draft_data = {"party_size": 2, "notes": "Test"}
    
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=6, is_authenticated=True),
    )
    
    response = client.post("/api/reservations/draft-save", json=draft_data)
    assert response.status_code == 200
    assert "user_id" not in response.json["draft"]


def test_draft_with_minimal_data(client, monkeypatch):
    """Drafts can be saved with minimal/partial data."""
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=7, is_authenticated=True),
    )
    
    minimal_draft = {"party_size": 2}
    response = client.post("/api/reservations/draft-save", json=minimal_draft)
    assert response.status_code == 200
    
    retrieved = response.json["draft"]
    assert retrieved["party_size"] == 2


def test_draft_shared_across_browsers_for_same_user(app, monkeypatch):
    """The same authenticated user can resume the draft from a different browser/client."""
    from features.reservations.presentation.api import reservation_routes as reservations_module_local

    client_a = app.test_client()
    client_b = app.test_client()

    monkeypatch.setattr(
        reservations_module_local,
        "current_user",
        FakeCurrentUser(user_id=99, is_authenticated=True),
    )

    draft_data = {
        "party_size": 5,
        "table_ids": [2],
        "start_ts": "2026-04-21T18:00:00",
        "end_ts": "2026-04-21T20:00:00",
        "games": [{"requested_game_id": 1, "game_copy_id": None}],
    }

    save_response = client_a.post("/api/reservations/draft-save", json=draft_data)
    assert save_response.status_code == 200

    retrieve_response = client_b.get("/api/reservations/draft")
    assert retrieve_response.status_code == 200
    assert retrieve_response.json["party_size"] == draft_data["party_size"]
    assert retrieve_response.json["table_ids"] == draft_data["table_ids"]
    assert retrieve_response.json["games"] == draft_data["games"]


def test_save_draft_empty_body(client, monkeypatch):
    """Empty body in draft save is handled gracefully."""
    monkeypatch.setattr(
        reservations_module,
        "current_user",
        FakeCurrentUser(user_id=8, is_authenticated=True),
    )
    
    response = client.post(
        "/api/reservations/draft-save",
        json={},
    )
    assert response.status_code == 200
    assert response.json["draft"] == {}
