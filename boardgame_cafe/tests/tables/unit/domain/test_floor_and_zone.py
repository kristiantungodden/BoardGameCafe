"""
Unit tests for Floor and Zone domain models.

These tests ensure the Floor and Zone entities properly validate data
and maintain their invariants.
"""
import pytest

from features.tables.domain.models.floor import Floor
from features.tables.domain.models.zone import Zone
from shared.domain.exceptions import ValidationError


class TestFloorCreation:
    """Test suite for Floor creation and validation."""
    
    def test_create_floor_with_required_fields_succeeds(self):
        """RULE: A floor can be created with number and name."""
        floor = Floor(
            number=1,
            name="Ground Floor",
        )
        
        assert floor.number == 1
        assert floor.name == "Ground Floor"
        assert floor.active is True
        assert floor.notes is None
    
    def test_create_floor_with_optional_fields_succeeds(self):
        """RULE: A floor can be created with optional notes and active flag."""
        floor = Floor(
            number=2,
            name="Second Floor",
            active=False,
            notes="Under renovation",
        )
        
        assert floor.number == 2
        assert floor.name == "Second Floor"
        assert floor.active is False
        assert floor.notes == "Under renovation"
    
    def test_create_floor_with_existing_id_succeeds(self):
        """RULE: A floor can be reconstituted from database with an id (via attribute assignment)."""
        floor = Floor(
            number=1,
            name="Main Floor",
        )
        
        # Floor doesn't have id in __init__, but can be assigned after creation
        floor.id = 42
        assert floor.id == 42
        assert floor.number == 1
        assert floor.name == "Main Floor"


class TestFloorValidation:
    """Test suite for Floor validation rules."""
    
    def test_floor_rejects_non_positive_number(self):
        """RULE: number must be a positive integer."""
        with pytest.raises(ValidationError, match="number must be a positive integer"):
            Floor(
                number=0,
                name="Invalid",
            )
        
        with pytest.raises(ValidationError, match="number must be a positive integer"):
            Floor(
                number=-1,
                name="Invalid",
            )
    
    def test_floor_rejects_empty_name(self):
        """RULE: name is required and cannot be empty."""
        with pytest.raises(ValidationError, match="name is required"):
            Floor(
                number=1,
                name="",
            )
        
        with pytest.raises(ValidationError, match="name is required"):
            Floor(
                number=1,
                name="   ",
            )
        
        with pytest.raises(ValidationError, match="name is required"):
            Floor(
                number=1,
                name="\t",
            )


class TestFloorSemantics:
    """Test suite for Floor domain semantics."""
    
    def test_floor_active_defaults_to_true(self):
        """RULE: Floor active status defaults to True."""
        floor = Floor(
            number=1,
            name="Main Floor",
        )
        
        assert floor.active is True
    
    def test_floor_can_be_deactivated(self):
        """RULE: Floor can be set as inactive."""
        floor = Floor(
            number=1,
            name="Closed Floor",
            active=False,
        )
        
        assert floor.active is False
    
    def test_floor_can_have_optional_notes(self):
        """RULE: Floor can have optional notes."""
        floor = Floor(
            number=1,
            name="Main Floor",
            notes="Large open space with natural lighting",
        )
        
        assert floor.notes == "Large open space with natural lighting"


class TestZoneCreation:
    """Test suite for Zone creation and validation."""
    
    def test_create_zone_with_required_fields_succeeds(self):
        """RULE: A zone can be created with floor and name."""
        zone = Zone(
            floor=1,
            name="Window Section",
        )
        
        assert zone.floor == 1
        assert zone.name == "Window Section"
        assert zone.active is True
        assert zone.notes is None
    
    def test_create_zone_with_optional_fields_succeeds(self):
        """RULE: A zone can be created with optional notes and active flag."""
        zone = Zone(
            floor=1,
            name="VIP Section",
            active=False,
            notes="Reserved for special events",
        )
        
        assert zone.floor == 1
        assert zone.name == "VIP Section"
        assert zone.active is False
        assert zone.notes == "Reserved for special events"
    
    def test_create_zone_with_existing_id_succeeds(self):
        """RULE: A zone can be reconstituted from database with an id (via attribute assignment)."""
        zone = Zone(
            floor=1,
            name="Main Area",
        )
        
        # Zone doesn't have id in __init__, but can be assigned after creation
        zone.id = 42
        assert zone.id == 42
        assert zone.floor == 1
        assert zone.name == "Main Area"


class TestZoneValidation:
    """Test suite for Zone validation rules."""
    
    def test_zone_rejects_non_positive_floor(self):
        """RULE: floor must be a positive integer."""
        with pytest.raises(ValidationError, match="floor must be a positive integer"):
            Zone(
                floor=0,
                name="Invalid",
            )
        
        with pytest.raises(ValidationError, match="floor must be a positive integer"):
            Zone(
                floor=-1,
                name="Invalid",
            )
    
    def test_zone_rejects_empty_name(self):
        """RULE: name is required and cannot be empty."""
        with pytest.raises(ValidationError, match="name is required"):
            Zone(
                floor=1,
                name="",
            )
        
        with pytest.raises(ValidationError, match="name is required"):
            Zone(
                floor=1,
                name="   ",
            )
        
        with pytest.raises(ValidationError, match="name is required"):
            Zone(
                floor=1,
                name="\t",
            )


class TestZoneSemantics:
    """Test suite for Zone domain semantics."""
    
    def test_zone_active_defaults_to_true(self):
        """RULE: Zone active status defaults to True."""
        zone = Zone(
            floor=1,
            name="Main Area",
        )
        
        assert zone.active is True
    
    def test_zone_can_be_deactivated(self):
        """RULE: Zone can be set as inactive."""
        zone = Zone(
            floor=1,
            name="Closed Section",
            active=False,
        )
        
        assert zone.active is False
    
    def test_zone_can_have_optional_notes(self):
        """RULE: Zone can have optional notes."""
        zone = Zone(
            floor=1,
            name="Family Section",
            notes="Quieter area suitable for families",
        )
        
        assert zone.notes == "Quieter area suitable for families"