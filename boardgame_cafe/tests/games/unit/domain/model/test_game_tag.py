"""
Unit tests for GameTag and GameTagLink domain models.

These tests ensure the GameTag and GameTagLink entities properly validate data
and maintain their invariants.
"""
import pytest

from features.games.domain.models.game_tag import GameTag
from features.games.domain.models.game_tag_link import GameTagLink
from shared.domain.exceptions import ValidationError


class TestGameTagCreation:
    """Test suite for GameTag creation and validation."""
    
    def test_create_game_tag_with_required_fields_succeeds(self):
        """RULE: A game tag can be created with id and name."""
        tag = GameTag(
            id=None,
            name="Strategy",
        )
        
        assert tag.name == "Strategy"
        assert tag.id is None
    
    def test_create_game_tag_trims_whitespace(self):
        """RULE: GameTag name should be trimmed of leading/trailing whitespace."""
        tag = GameTag(
            id=None,
            name="  Family-Friendly  ",
        )
        
        assert tag.name == "Family-Friendly"
    
    def test_create_game_tag_with_existing_id_succeeds(self):
        """RULE: A game tag can be reconstituted from database with an id."""
        tag = GameTag(
            id=42,
            name="Cooperative",
        )
        
        assert tag.id == 42
        assert tag.name == "Cooperative"


class TestGameTagValidation:
    """Test suite for GameTag validation rules."""
    
    def test_game_tag_rejects_empty_name(self):
        """RULE: Tag name cannot be empty."""
        with pytest.raises(ValidationError, match="Tag name cannot be empty"):
            GameTag(id=None, name="")
    
    def test_game_tag_rejects_whitespace_only_name(self):
        """RULE: Tag name cannot be only whitespace."""
        with pytest.raises(ValidationError, match="Tag name cannot be empty"):
            GameTag(id=None, name="   ")
        
        with pytest.raises(ValidationError, match="Tag name cannot be empty"):
            GameTag(id=None, name="\t")
        
        with pytest.raises(ValidationError, match="Tag name cannot be empty"):
            GameTag(id=None, name="\n")


class TestGameTagSemantics:
    """Test suite for GameTag domain semantics."""
    
    def test_game_tag_name_is_stripped(self):
        """RULE: GameTag name should be stripped after creation."""
        tag = GameTag(id=None, name="  Party  ")
        assert tag.name == "Party"
    
    def test_game_tag_accepts_various_valid_names(self):
        """RULE: GameTag should accept various valid tag names."""
        valid_names = [
            "Strategy",
            "Family-Friendly",
            "2-Player",
            "Quick Play",
            "Complex",
            "Educational",
        ]
        
        for name in valid_names:
            tag = GameTag(id=None, name=name)
            assert tag.name == name


class TestGameTagLinkCreation:
    """Test suite for GameTagLink creation and validation."""
    
    def test_create_game_tag_link_with_required_fields_succeeds(self):
        """RULE: A game tag link can be created with game_id and game_tag_id."""
        link = GameTagLink(
            game_id=1,
            game_tag_id=10,
        )
        
        assert link.game_id == 1
        assert link.game_tag_id == 10
        assert link.id is None
    
    def test_create_game_tag_link_with_existing_id_succeeds(self):
        """RULE: A game tag link can be reconstituted from database with an id."""
        link = GameTagLink(
            game_id=1,
            game_tag_id=10,
            id=42,
        )
        
        assert link.id == 42
        assert link.game_id == 1
        assert link.game_tag_id == 10


class TestGameTagLinkValidation:
    """Test suite for GameTagLink validation rules."""
    
    def test_game_tag_link_rejects_non_positive_game_id(self):
        """RULE: game_id must be a positive integer."""
        with pytest.raises(ValidationError, match="game_id must be a positive integer"):
            GameTagLink(
                game_id=0,
                game_tag_id=10,
            )
        
        with pytest.raises(ValidationError, match="game_id must be a positive integer"):
            GameTagLink(
                game_id=-1,
                game_tag_id=10,
            )
    
    def test_game_tag_link_rejects_non_positive_game_tag_id(self):
        """RULE: game_tag_id must be a positive integer."""
        with pytest.raises(ValidationError, match="game_tag_id must be a positive integer"):
            GameTagLink(
                game_id=1,
                game_tag_id=0,
            )
        
        with pytest.raises(ValidationError, match="game_tag_id must be a positive integer"):
            GameTagLink(
                game_id=1,
                game_tag_id=-10,
            )


class TestGameTagLinkSemantics:
    """Test suite for GameTagLink domain semantics."""
    
    def test_game_tag_link_represents_association(self):
        """RULE: GameTagLink represents an association between a game and a tag."""
        link = GameTagLink(
            game_id=5,
            game_tag_id=20,
        )
        
        # The link simply associates a game with a tag
        assert link.game_id == 5
        assert link.game_tag_id == 20
        
        # No additional behavior - it's a pure link entity