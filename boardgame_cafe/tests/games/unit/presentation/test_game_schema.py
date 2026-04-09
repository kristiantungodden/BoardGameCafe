from decimal import Decimal

import pytest
from pydantic import ValidationError

from features.games.presentation.schemas.game_schema import (
    GameCreateRequest,
    GameTagCreateRequest,
    GameTagLinkCreateRequest,
    GameUpdateRequest,
)


def test_game_create_request_validates_successfully():
    payload = GameCreateRequest.model_validate(
        {
            "title": "Catan",
            "min_players": 3,
            "max_players": 4,
            "playtime_min": 90,
            "complexity": Decimal("2.5"),
            "description": "Classic strategy game",
        }
    )

    assert payload.title == "Catan"
    assert payload.min_players == 3
    assert payload.max_players == 4
    assert payload.complexity == Decimal("2.5")


def test_game_create_request_rejects_invalid_player_range():
    with pytest.raises(ValidationError) as exc:
        GameCreateRequest.model_validate(
            {
                "title": "Catan",
                "min_players": 5,
                "max_players": 3,
                "playtime_min": 90,
                "complexity": Decimal("2.5"),
            }
        )

    assert "min_players cannot be greater than max_players" in str(exc.value)


def test_game_update_request_rejects_blank_title():
    with pytest.raises(ValidationError):
        GameUpdateRequest.model_validate({"title": "   "})


def test_game_update_request_allows_partial_payload():
    payload = GameUpdateRequest.model_validate({"playtime_min": 120})

    assert payload.title is None
    assert payload.playtime_min == 120


def test_game_tag_create_request_rejects_blank_name():
    with pytest.raises(ValidationError):
        GameTagCreateRequest.model_validate({"name": "   "})


def test_game_tag_link_request_requires_positive_tag_id():
    with pytest.raises(ValidationError):
        GameTagLinkCreateRequest.model_validate({"tag_id": 0})