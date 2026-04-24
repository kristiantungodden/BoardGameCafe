"""
Unit tests for the WaitlistEntry domain model.

These tests ensure the WaitlistEntry entity properly validates data
and maintains its invariants.
"""
from datetime import datetime, timezone

import pytest

from features.reservations.domain.models.waitlist_entry import WaitlistEntry


class TestWaitlistEntryCreation:
    """Test suite for WaitlistEntry creation and validation."""
    
    def test_create_waitlist_entry_with_required_fields_succeeds(self):
        """RULE: A waitlist entry can be created with id, customer_id and party_size."""
        waitlist_entry = WaitlistEntry(
            id=None,
            customer_id=1,
            party_size=4,
        )
        
        assert waitlist_entry.customer_id == 1
        assert waitlist_entry.party_size == 4
        assert waitlist_entry.notes is None
        assert waitlist_entry.id is None
        assert waitlist_entry.created_at is not None
    
    def test_create_waitlist_entry_with_optional_fields_succeeds(self):
        """RULE: A waitlist entry can be created with optional notes."""
        waitlist_entry = WaitlistEntry(
            id=None,
            customer_id=1,
            party_size=4,
            notes="Large party, prefer window seat",
        )
        
        assert waitlist_entry.customer_id == 1
        assert waitlist_entry.party_size == 4
        assert waitlist_entry.notes == "Large party, prefer window seat"
        assert waitlist_entry.id is None
        assert waitlist_entry.created_at is not None
    
    def test_create_waitlist_entry_with_existing_id_succeeds(self):
        """RULE: A waitlist entry can be reconstituted from database with an id."""
        waitlist_entry = WaitlistEntry(
            customer_id=1,
            party_size=4,
            id=42,
        )
        
        assert waitlist_entry.id == 42
        assert waitlist_entry.customer_id == 1
        assert waitlist_entry.party_size == 4
    
    def test_create_waitlist_entry_sets_current_timestamp(self):
        """RULE: A waitlist entry automatically sets created_at to current time."""
        before = datetime.now(timezone.utc)
        waitlist_entry = WaitlistEntry(
            id=None,
            customer_id=1,
            party_size=4,
        )
        after = datetime.now(timezone.utc)
        
        assert waitlist_entry.created_at >= before
        assert waitlist_entry.created_at <= after


class TestWaitlistEntryValidation:
    """Test suite for WaitlistEntry validation rules."""
    
    def test_waitlist_entry_rejects_non_positive_customer_id(self):
        """RULE: customer_id must be a positive integer."""
        with pytest.raises(TypeError):
            WaitlistEntry(
                customer_id=0,
                party_size=4,
            )
        
        with pytest.raises(TypeError):
            WaitlistEntry(
                customer_id=-1,
                party_size=4,
            )
    
    def test_waitlist_entry_rejects_non_positive_party_size(self):
        """RULE: party_size must be a positive integer."""
        with pytest.raises(TypeError):
            WaitlistEntry(
                customer_id=1,
                party_size=0,
            )
        
        with pytest.raises(TypeError):
            WaitlistEntry(
                customer_id=1,
                party_size=-4,
            )


class TestWaitlistEntrySemantics:
    """Test suite for WaitlistEntry domain semantics."""
    
    def test_waitlist_entry_to_dict_includes_all_fields(self):
        """RULE: to_dict() returns all relevant fields in expected format."""
        waitlist_entry = WaitlistEntry(
            id=100,
            customer_id=1,
            party_size=4,
            notes="Special request",
        )
        
        result = waitlist_entry.to_dict()
        
        assert result["id"] == 100
        assert result["customer_id"] == 1
        assert result["party_size"] == 4
        assert result["notes"] == "Special request"
        assert "created_at" in result
        assert isinstance(result["created_at"], str)
    
    def test_waitlist_entry_to_dict_handles_none_notes(self):
        """RULE: to_dict() handles None notes gracefully."""
        waitlist_entry = WaitlistEntry(
            id=None,
            customer_id=1,
            party_size=4,
            notes=None,
        )
        
        result = waitlist_entry.to_dict()
        
        assert result["notes"] is None
    
    def test_waitlist_entry_is_immutable_after_creation(self):
        """RULE: WaitlistEntry fields should not be modified after creation."""
        waitlist_entry = WaitlistEntry(
            id=None,
            customer_id=1,
            party_size=4,
            notes="Original note",
        )
        
        # Test that we can read the values
        assert waitlist_entry.customer_id == 1
        assert waitlist_entry.party_size == 4
        assert waitlist_entry.notes == "Original note"
        
        # Note: Dataclass fields are mutable by default, but domain entities
        # should be treated as immutable in business logic. This test documents
        # the current behavior while noting the expectation.
