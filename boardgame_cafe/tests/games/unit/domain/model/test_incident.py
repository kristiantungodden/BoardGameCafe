"""
Unit tests for the Incident domain model.

These tests ensure the Incident entity properly validates data
and maintains its invariants.
"""
import pytest

from features.games.domain.models.incident import Incident, VALID_INCIDENT_TYPES
from shared.domain.exceptions import ValidationError


class TestIncidentCreation:
    """Test suite for Incident creation and validation."""
    
    def test_create_incident_with_required_fields_succeeds(self):
        """RULE: An incident can be created with game_copy_id, reported_by, incident_type, and note."""
        incident = Incident(
            game_copy_id=1,
            reported_by=10,
            incident_type="damage",
            note="Broken corner piece",
        )
        
        assert incident.game_copy_id == 1
        assert incident.reported_by == 10
        assert incident.incident_type == "damage"
        assert incident.note == "Broken corner piece"
        assert incident.id is None
        assert incident.created_at is not None
    
    def test_create_incident_with_loss_type_succeeds(self):
        """RULE: An incident can be created with 'loss' incident type."""
        incident = Incident(
            game_copy_id=1,
            reported_by=10,
            incident_type="loss",
            note="Missing from shelf during inventory",
        )
        
        assert incident.incident_type == "loss"
    
    def test_create_incident_with_existing_id_succeeds(self):
        """RULE: An incident can be reconstituted from database with an id."""
        incident = Incident(
            game_copy_id=1,
            reported_by=10,
            incident_type="damage",
            note="Broken corner piece",
            id=42,
        )
        
        assert incident.id == 42
        assert incident.game_copy_id == 1
        assert incident.reported_by == 10


class TestIncidentValidation:
    """Test suite for Incident validation rules."""
    
    def test_incident_rejects_non_positive_game_copy_id(self):
        """RULE: game_copy_id must be a positive integer."""
        with pytest.raises(ValidationError, match="game_copy_id must be a positive integer"):
            Incident(
                game_copy_id=0,
                reported_by=10,
                incident_type="damage",
                note="Test note",
            )
        
        with pytest.raises(ValidationError, match="game_copy_id must be a positive integer"):
            Incident(
                game_copy_id=-1,
                reported_by=10,
                incident_type="damage",
                note="Test note",
            )
    
    def test_incident_rejects_non_positive_reported_by(self):
        """RULE: reported_by must be a positive integer."""
        with pytest.raises(ValidationError, match="reported_by must be a positive integer"):
            Incident(
                game_copy_id=1,
                reported_by=0,
                incident_type="damage",
                note="Test note",
            )
        
        with pytest.raises(ValidationError, match="reported_by must be a positive integer"):
            Incident(
                game_copy_id=1,
                reported_by=-10,
                incident_type="damage",
                note="Test note",
            )
    
    def test_incident_rejects_invalid_incident_type(self):
        """RULE: incident_type must be one of VALID_INCIDENT_TYPES."""
        valid_types = ", ".join(sorted(VALID_INCIDENT_TYPES))
        
        with pytest.raises(ValidationError, match="incident_type must be one of"):
            Incident(
                game_copy_id=1,
                reported_by=10,
                incident_type="theft",
                note="Test note",
            )
        
        with pytest.raises(ValidationError, match="incident_type must be one of"):
            Incident(
                game_copy_id=1,
                reported_by=10,
                incident_type="",
                note="Test note",
            )
        
        with pytest.raises(ValidationError, match="incident_type must be one of"):
            Incident(
                game_copy_id=1,
                reported_by=10,
                incident_type="DAMAGE",  # Case sensitive
                note="Test note",
            )
    
    def test_incident_rejects_empty_note(self):
        """RULE: note cannot be empty."""
        with pytest.raises(ValidationError, match="note cannot be empty"):
            Incident(
                game_copy_id=1,
                reported_by=10,
                incident_type="damage",
                note="",
            )
        
        with pytest.raises(ValidationError, match="note cannot be empty"):
            Incident(
                game_copy_id=1,
                reported_by=10,
                incident_type="damage",
                note="   ",
            )
        
        with pytest.raises(ValidationError, match="note cannot be empty"):
            Incident(
                game_copy_id=1,
                reported_by=10,
                incident_type="damage",
                note="\t",
            )


class TestIncidentSemantics:
    """Test suite for Incident domain semantics."""
    
    def test_incident_accepts_valid_incident_types(self):
        """RULE: Incident should accept all valid incident types."""
        for incident_type in VALID_INCIDENT_TYPES:
            incident = Incident(
                game_copy_id=1,
                reported_by=10,
                incident_type=incident_type,
                note="Test note",
            )
            assert incident.incident_type == incident_type
    
    def test_incident_accepts_multiline_notes(self):
        """RULE: Incident notes can contain multiple lines."""
        incident = Incident(
            game_copy_id=1,
            reported_by=10,
            incident_type="damage",
            note="First line of description.\nSecond line with more details.\nThird line with resolution.",
        )
        
        assert incident.note == "First line of description.\nSecond line with more details.\nThird line with resolution."
    
    def test_incident_accepts_long_notes(self):
        """RULE: Incident notes can be lengthy."""
        long_note = "A" * 1000
        incident = Incident(
            game_copy_id=1,
            reported_by=10,
            incident_type="damage",
            note=long_note,
        )
        
        assert incident.note == long_note
    
    def test_incident_created_at_is_set_automatically(self):
        """RULE: created_at is automatically set on creation."""
        from datetime import datetime, timezone
        
        before = datetime.now(timezone.utc)
        incident = Incident(
            game_copy_id=1,
            reported_by=10,
            incident_type="damage",
            note="Test note",
        )
        after = datetime.now(timezone.utc)
        
        assert incident.created_at >= before
        assert incident.created_at <= after
    
    def test_incident_represents_damage_or_loss(self):
        """RULE: Incident domain semantics - represents damage or loss reports."""
        # Damage incident
        damage_incident = Incident(
            game_copy_id=1,
            reported_by=10,
            incident_type="damage",
            note="Water damage to board",
        )
        assert damage_incident.incident_type == "damage"
        
        # Loss incident
        loss_incident = Incident(
            game_copy_id=1,
            reported_by=10,
            incident_type="loss",
            note="Missing during inventory check",
        )
        assert loss_incident.incident_type == "loss"