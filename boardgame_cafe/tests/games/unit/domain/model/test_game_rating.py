"""
Unit tests for the GameRating domain model.

These tests ensure the GameRating entity properly validates data
and maintains its invariants.
"""
import pytest

from features.games.domain.models.game_rating import GameRating


class TestGameRatingCreation:
    """Test suite for GameRating creation and validation."""
    
    def test_create_game_rating_with_required_fields_succeeds(self):
        """RULE: A game rating can be created with id, customer_id, game_id, and stars."""
        rating = GameRating(
            id=None,
            customer_id=1,
            game_id=42,
            stars=5,
        )
        
        assert rating.customer_id == 1
        assert rating.game_id == 42
        assert rating.stars == 5
        assert rating.comment is None
        assert rating.id is None
        assert rating.created_at is None
    
    def test_create_game_rating_with_optional_comment_succeeds(self):
        """RULE: A game rating can be created with an optional comment."""
        rating = GameRating(
            id=None,
            customer_id=1,
            game_id=42,
            stars=4,
            comment="Great game for beginners!",
        )
        
        assert rating.customer_id == 1
        assert rating.game_id == 42
        assert rating.stars == 4
        assert rating.comment == "Great game for beginners!"
        assert rating.id is None
    
    def test_create_game_rating_with_existing_id_succeeds(self):
        """RULE: A game rating can be reconstituted from database with an id."""
        rating = GameRating(
            id=100,
            customer_id=1,
            game_id=42,
            stars=3,
            created_at="2026-04-10T18:00:00Z",
        )
        
        assert rating.id == 100
        assert rating.customer_id == 1
        assert rating.game_id == 42
        assert rating.stars == 3
        assert rating.created_at == "2026-04-10T18:00:00Z"


class TestGameRatingValidation:
    """Test suite for GameRating validation rules."""
    
    def test_game_rating_rejects_non_positive_customer_id(self):
        """RULE: customer_id must be a positive integer."""
        rating = GameRating(id=None, customer_id=0, game_id=1, stars=5)
        with pytest.raises(ValueError, match="customer_id must be a positive integer"):
            rating.validate()
        
        rating = GameRating(id=None, customer_id=-1, game_id=1, stars=5)
        with pytest.raises(ValueError, match="customer_id must be a positive integer"):
            rating.validate()
    
    def test_game_rating_rejects_non_positive_game_id(self):
        """RULE: game_id must be a positive integer."""
        rating = GameRating(id=None, customer_id=1, game_id=0, stars=5)
        with pytest.raises(ValueError, match="game_id must be a positive integer"):
            rating.validate()
        
        rating = GameRating(id=None, customer_id=1, game_id=-1, stars=5)
        with pytest.raises(ValueError, match="game_id must be a positive integer"):
            rating.validate()
    
    def test_game_rating_rejects_invalid_stars_values(self):
        """RULE: stars must be an integer between 1 and 5."""
        # Test stars = 0
        rating = GameRating(id=None, customer_id=1, game_id=1, stars=0)
        with pytest.raises(ValueError, match="stars must be an integer between 1 and 5"):
            rating.validate()
        
        # Test stars = 6
        rating = GameRating(id=None, customer_id=1, game_id=1, stars=6)
        with pytest.raises(ValueError, match="stars must be an integer between 1 and 5"):
            rating.validate()
        
        # Test stars > 5
        rating = GameRating(id=None, customer_id=1, game_id=1, stars=10)
        with pytest.raises(ValueError, match="stars must be an integer between 1 and 5"):
            rating.validate()
    
    def test_game_rating_accepts_valid_star_range(self):
        """RULE: stars must accept values 1, 2, 3, 4, and 5."""
        for stars in [1, 2, 3, 4, 5]:
            rating = GameRating(id=None, customer_id=1, game_id=1, stars=stars)
            # Should not raise any exception
            rating.validate()
            assert rating.stars == stars
    
    def test_game_rating_rejects_non_integer_stars(self):
        """RULE: stars must be an integer (not float or string)."""
        rating = GameRating(id=None, customer_id=1, game_id=1, stars=3.5)
        with pytest.raises(ValueError, match="stars must be an integer between 1 and 5"):
            rating.validate()
        
        rating = GameRating(id=None, customer_id=1, game_id=1, stars="5")
        with pytest.raises(ValueError, match="stars must be an integer between 1 and 5"):
            rating.validate()


class TestGameRatingSemantics:
    """Test suite for GameRating domain semantics."""
    
    def test_game_rating_can_have_optional_comment(self):
        """RULE: A game rating can have an optional comment."""
        rating_with_comment = GameRating(
            id=None,
            customer_id=1,
            game_id=1,
            stars=5,
            comment="Excellent!",
        )
        assert rating_with_comment.comment == "Excellent!"
        
        rating_without_comment = GameRating(
            id=None,
            customer_id=1,
            game_id=1,
            stars=4,
        )
        assert rating_without_comment.comment is None
    
    def test_game_rating_can_have_created_at_timestamp(self):
        """RULE: A game rating can have an optional created_at timestamp."""
        rating = GameRating(
            id=None,
            customer_id=1,
            game_id=1,
            stars=4,
            created_at="2026-04-10T18:00:00Z",
        )
        assert rating.created_at == "2026-04-10T18:00:00Z"
        
        rating_no_timestamp = GameRating(
            id=None,
            customer_id=1,
            game_id=1,
            stars=4,
        )
        assert rating_no_timestamp.created_at is None
