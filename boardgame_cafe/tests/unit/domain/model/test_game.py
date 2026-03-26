# tests/test_game_model.py
import pytest
from src.domain.models.game import Game

def test_is_playable_by():
    game = Game(id=None, title="Test Game", min_players=2, max_players=5, playtime_min=30, complexity=1.5)
    assert game.is_playable_by(2) is True
    assert game.is_playable_by(4) is True
    assert game.is_playable_by(1) is False
    assert game.is_playable_by(6) is False

def test_update_details_valid():
    game = Game(
        id=42,  # assign a test id
        title="Old",
        min_players=2,
        max_players=4,
        playtime_min=30,
        complexity=1.0,
        description="Old desc",
        image_url="old_url"
    )

    # Save original id to test it doesn’t change
    original_id = game.id

    # Update all fields
    game.update_details(
        title="New",
        min_players=3,
        max_players=5,
        playtime_min=45,
        complexity=2.0,
        description="New description",
        image_url="new_url"
    )

    # Test ALL attributes
    assert game.id == original_id  # id should not change
    assert game.title == "New"
    assert game.min_players == 3
    assert game.max_players == 5
    assert game.playtime_min == 45
    assert game.complexity == 2.0
    assert game.description == "New description"
    assert game.image_url == "new_url"

def test_update_details_invalid():
    game = Game(id=42, title="Old", min_players=2, max_players=4, playtime_min=30, complexity=1.0)
    with pytest.raises(ValueError):
        game.update_details(
            title="New",
            min_players=5,  # min > max
            max_players=3,
            playtime_min=45,
            complexity=2.0,
            description="desc",
            image_url="url"
        )
    assert game.id == 42  # id should remain unchanged even after failed update