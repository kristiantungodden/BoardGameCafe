from datetime import datetime, timezone

import pytest

from features.games.domain.models.game_copy import GameCopy
from shared.domain.exceptions import InvalidStatusTransition, ValidationError


def _make_copy(**overrides) -> GameCopy:
    data = {
        "game_id": 1,
        "copy_code": "CATAN-001",
        "status": "available",
        "location": "Shelf A",
        "condition_note": None,
    }
    data.update(overrides)
    return GameCopy(**data)


def test_create_game_copy_with_valid_data():
    game_copy = _make_copy()

    assert game_copy.game_id == 1
    assert game_copy.copy_code == "CATAN-001"
    assert game_copy.status == "available"


def test_create_game_copy_rejects_non_positive_game_id():
    with pytest.raises(ValidationError, match="game_id must be a positive integer"):
        _make_copy(game_id=0)


def test_create_game_copy_rejects_blank_copy_code():
    with pytest.raises(ValidationError, match="copy_code cannot be empty"):
        _make_copy(copy_code="   ")


def test_reserve_changes_status_from_available_to_reserved():
    game_copy = _make_copy(status="available")

    game_copy.reserve()

    assert game_copy.status == "reserved"


def test_reserve_rejects_transition_from_in_use():
    game_copy = _make_copy(status="in_use")

    with pytest.raises(InvalidStatusTransition, match="Cannot reserve game copy"):
        game_copy.reserve()


def test_mark_in_use_allowed_from_available_and_reserved():
    from_available = _make_copy(status="available")
    from_available.mark_in_use()
    assert from_available.status == "in_use"

    from_reserved = _make_copy(status="reserved")
    from_reserved.mark_in_use()
    assert from_reserved.status == "in_use"


def test_return_to_shelf_sets_available_and_updates_location_when_provided():
    game_copy = _make_copy(status="in_use", location="Table 3")

    game_copy.return_to_shelf(location="Shelf B")

    assert game_copy.status == "available"
    assert game_copy.location == "Shelf B"


def test_send_to_maintenance_rejects_when_already_in_maintenance():
    game_copy = _make_copy(status="maintenance")

    with pytest.raises(InvalidStatusTransition, match="already in maintenance"):
        game_copy.send_to_maintenance()


def test_move_rejects_blank_location():
    game_copy = _make_copy()

    with pytest.raises(ValidationError, match="new_location cannot be empty"):
        game_copy.move("   ")


def test_update_condition_note_supports_none_and_updates_timestamp():
    game_copy = _make_copy(condition_note="Slightly worn")
    before = datetime.now(timezone.utc)

    game_copy.update_condition_note(None)

    assert game_copy.condition_note is None
    assert game_copy.updated_at >= before
