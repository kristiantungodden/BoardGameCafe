import pytest
from pydantic import ValidationError

from features.games.presentation.schemas.game_copy_schema import (
    GameCopyConditionNoteUpdateRequest,
    GameCopyCreateRequest,
    GameCopyLocationUpdateRequest,
    GameCopyStatusUpdateRequest,
)


def test_game_copy_create_request_trims_fields():
    payload = GameCopyCreateRequest.model_validate(
        {
            "game_id": 1,
            "copy_code": "  CATAN-001  ",
            "status": "available",
            "location": "  Shelf A  ",
            "condition_note": "  Good condition  ",
        }
    )

    assert payload.copy_code == "CATAN-001"
    assert payload.location == "Shelf A"
    assert payload.condition_note == "Good condition"


def test_game_copy_create_request_rejects_blank_copy_code():
    with pytest.raises(ValidationError, match="copy_code cannot be empty"):
        GameCopyCreateRequest.model_validate(
            {
                "game_id": 1,
                "copy_code": "   ",
                "status": "available",
            }
        )


def test_game_copy_create_request_rejects_invalid_status():
    with pytest.raises(ValidationError, match="status must be one of"):
        GameCopyCreateRequest.model_validate(
            {
                "game_id": 1,
                "copy_code": "CATAN-001",
                "status": "lost",
            }
        )


def test_game_copy_status_update_request_accepts_known_actions():
    for action in ["reserve", "use", "return", "maintenance"]:
        payload = GameCopyStatusUpdateRequest.model_validate({"action": action})
        assert payload.action == action


def test_game_copy_status_update_request_rejects_invalid_action():
    with pytest.raises(ValidationError, match="action must be one of"):
        GameCopyStatusUpdateRequest.model_validate({"action": "repair"})


def test_game_copy_location_update_request_rejects_blank_location():
    with pytest.raises(ValidationError, match="location cannot be empty"):
        GameCopyLocationUpdateRequest.model_validate({"location": "   "})


def test_game_copy_condition_note_blank_is_normalized_to_none():
    payload = GameCopyConditionNoteUpdateRequest.model_validate(
        {"condition_note": "   "}
    )

    assert payload.condition_note is None
