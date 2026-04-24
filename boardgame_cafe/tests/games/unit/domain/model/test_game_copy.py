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


class TestGameCopyEdgeCases:
    """Test suite for GameCopy edge cases and boundary conditions."""
    
    def test_mark_lost_changes_status_from_any_non_lost(self):
        """RULE: mark_lost can be called from any status except 'lost'."""
        for status in ["available", "reserved", "in_use", "maintenance"]:
            game_copy = _make_copy(status=status)
            game_copy.mark_lost()
            assert game_copy.status == "lost"
    
    def test_mark_lost_rejects_already_lost(self):
        """RULE: Cannot mark a game copy as lost if it's already lost."""
        game_copy = _make_copy(status="lost")
        with pytest.raises(InvalidStatusTransition, match="already marked as lost"):
            game_copy.mark_lost()
    
    def test_send_to_maintenance_from_various_statuses(self):
        """RULE: send_to_maintenance works from any status except 'maintenance'."""
        for status in ["available", "reserved", "in_use", "lost"]:
            game_copy = _make_copy(status=status)
            game_copy.send_to_maintenance()
            assert game_copy.status == "maintenance"
    
    def test_return_to_shelf_works_from_any_status(self):
        """RULE: return_to_shelf can be called from any status."""
        for status in ["available", "reserved", "in_use", "maintenance", "lost"]:
            game_copy = _make_copy(status=status)
            game_copy.return_to_shelf()
            assert game_copy.status == "available"
    
    def test_return_to_shelf_without_location(self):
        """RULE: return_to_shelf can be called without a location."""
        game_copy = _make_copy(status="in_use", location="Table 3")
        game_copy.return_to_shelf()
        assert game_copy.status == "available"
        # Location should remain unchanged when not provided
        assert game_copy.location == "Table 3"
    
    def test_return_to_shelf_with_empty_location(self):
        """RULE: return_to_shelf with empty location doesn't change location."""
        game_copy = _make_copy(status="in_use", location="Table 3")
        game_copy.return_to_shelf(location="")
        assert game_copy.status == "available"
        assert game_copy.location == "Table 3"
    
    def test_return_to_shelf_with_whitespace_location(self):
        """RULE: return_to_shelf with whitespace-only location doesn't change location."""
        game_copy = _make_copy(status="in_use", location="Table 3")
        game_copy.return_to_shelf(location="   ")
        assert game_copy.status == "available"
        assert game_copy.location == "Table 3"
    
    def test_move_updates_location_and_timestamp(self):
        """RULE: move updates both location and timestamp."""
        game_copy = _make_copy(location="Shelf A")
        before = datetime.now(timezone.utc)
        
        game_copy.move("Shelf B")
        
        assert game_copy.location == "Shelf B"
        assert game_copy.updated_at >= before
    
    def test_is_available_reflects_status(self):
        """RULE: is_available() returns True only when status is 'available'."""
        for status in ["available", "reserved", "in_use", "maintenance", "lost"]:
            game_copy = _make_copy(status=status)
            expected = status == "available"
            assert game_copy.is_available() == expected
    
    def test_game_copy_status_transitions_are_valid(self):
        """RULE: All valid status transitions should work correctly."""
        # available -> reserved -> in_use -> available
        game_copy = _make_copy(status="available")
        game_copy.reserve()
        assert game_copy.status == "reserved"
        game_copy.mark_in_use()
        assert game_copy.status == "in_use"
        game_copy.return_to_shelf("Shelf A")
        assert game_copy.status == "available"
        
        # available -> in_use -> available
        game_copy = _make_copy(status="available")
        game_copy.mark_in_use()
        assert game_copy.status == "in_use"
        game_copy.return_to_shelf("Shelf A")
        assert game_copy.status == "available"
        
        # available -> maintenance -> available
        game_copy = _make_copy(status="available")
        game_copy.send_to_maintenance()
        assert game_copy.status == "maintenance"
        game_copy.return_to_shelf("Shelf A")
        assert game_copy.status == "available"
    
    def test_game_copy_updated_at_changes_on_operations(self):
        """RULE: updated_at should change on state-modifying operations."""
        game_copy = _make_copy()
        original_updated_at = game_copy.updated_at
        
        game_copy.reserve()
        assert game_copy.updated_at >= original_updated_at
        
        original_updated_at = game_copy.updated_at
        game_copy.mark_in_use()
        assert game_copy.updated_at >= original_updated_at
