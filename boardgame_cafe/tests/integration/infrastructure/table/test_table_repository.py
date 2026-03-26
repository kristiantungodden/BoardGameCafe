"""Core CRUD and error handling tests for TableRepository."""
from domain.models.table import Table
from infrastructure.repositories import TableRepository

import pytest

def test_table_repository_add(app, repo):
    """Test adding a new table to the repository."""
    new_table = Table(number=1, capacity=4, zone="A", features={"near_window": True}, status="available")
    added_table = repo.add(new_table)

    assert added_table.id is not None
    assert added_table.number == new_table.number
    assert added_table.capacity == new_table.capacity
    assert added_table.zone == new_table.zone
    assert added_table.features == new_table.features
    assert added_table.status == new_table.status


def test_table_repository_get_by_id(app, repo):
    """Test retrieving a table by ID."""
    new_table = Table(number=2, capacity=6, zone="B", features={"near_window": False}, status="available")
    added_table = repo.add(new_table)

    retrieved_table = repo.get_by_id(added_table.id)
    assert retrieved_table is not None
    assert retrieved_table.id == added_table.id
    assert retrieved_table.number == added_table.number
    assert retrieved_table.capacity == added_table.capacity
    assert retrieved_table.zone == added_table.zone
    assert retrieved_table.features == added_table.features
    assert retrieved_table.status == added_table.status


def test_table_repository_get_by_id_with_unknown_id_returns_none(app, repo):
    """Test that get_by_id returns None for non-existent table."""
    result = repo.get_by_id(99999)
    assert result is None


def test_table_repository_list(app, repo):
    """Test listing all tables returns all added tables."""
    table1 = Table(number=3, capacity=2, zone="C", features={"near_window": True}, status="available")
    table2 = Table(number=4, capacity=8, zone="D", features={"near_window": False}, status="occupied")
    added1 = repo.add(table1)
    added2 = repo.add(table2)

    tables = repo.list()
    
    # Verify exactly these tables are in the list (by ID)
    ids_returned = {t.id for t in tables}
    assert added1.id in ids_returned, f"Added table {added1.id} not found in list()"
    assert added2.id in ids_returned, f"Added table {added2.id} not found in list()"
    
    # Verify the returned objects have correct data
    assert any(t.id == added1.id and t.number == 3 and t.capacity == 2 and t.zone == "C" for t in tables)
    assert any(t.id == added2.id and t.number == 4 and t.capacity == 8 and t.zone == "D" for t in tables)


def test_table_repository_update(app, repo):
    """Test updating a table persists changes to the repository."""
    new_table = Table(number=5, capacity=4, zone="E", features={"near_window": True}, status="available")
    added_table = repo.add(new_table)
    table_id = added_table.id

    # Update table details
    added_table.capacity = 6
    added_table.status = "occupied"
    updated_table = repo.update(added_table)

    # Verify returned object has updates
    assert updated_table.id == table_id
    assert updated_table.capacity == 6
    assert updated_table.status == "occupied"

    # CRITICAL: Verify changes persisted to repository (re-fetch fresh)
    persisted_table = repo.get_by_id(table_id)
    assert persisted_table is not None, "Updated table not found in repository"
    assert persisted_table.capacity == 6, f"Capacity not persisted: expected 6, got {persisted_table.capacity}"
    assert persisted_table.status == "occupied", f"Status not persisted: expected occupied, got {persisted_table.status}"
    assert persisted_table.number == 5, "Number should not change on update"


def test_table_repository_delete(app, repo):
    """Test deleting a table."""
    new_table = Table(number=6, capacity=4, zone="F", features={"near_window": False}, status="available")
    added_table = repo.add(new_table)

    repo.delete(added_table.id)
    deleted_table = repo.get_by_id(added_table.id)
    assert deleted_table is None


def test_table_repository_count_by_status(app, repo):
    """Test aggregation: counting tables by status."""
    from conftest import seed_tables
    seed_tables(repo)

    counts = repo.count_by_status()

    assert counts["available"] == 2
    assert counts["occupied"] == 1
    assert counts["maintenance"] == 1
    assert counts["reserved"] == 1


def test_table_repository_update_without_id_raises(app, repo):
    """Test that updating an unsaved table raises ValueError."""
    unsaved = Table(number=99, capacity=4, zone="Z", features={}, status="available")

    with pytest.raises(ValueError, match="Cannot update table without an id"):
        repo.update(unsaved)


def test_table_repository_delete_missing_id_raises(app, repo):
    """Test that deleting a non-existent table raises ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        repo.delete(99999)


def test_table_repository_data_normalization_string_to_int_roundtrip(app, repo):
    """Test that table_nr (string in DB) is correctly normalized to number (int in domain)."""
    # Add a table with specific number
    table = Table(number=42, capacity=4, zone="TEST", features={}, status="available")
    added = repo.add(table)
    
    # Retrieve and verify the number is still an int and has correct value
    retrieved = repo.get_by_id(added.id)
    
    assert isinstance(retrieved.number, int)
    assert retrieved.number == 42
    
    # Also check it works in list
    result = repo.list()
    assert any(t.number == 42 and isinstance(t.number, int) for t in result)


def test_table_repository_validation_rejects_invalid_status(app, repo):
    """Test that repository rejects invalid status values at domain layer."""
    # The domain model validates status in __post_init__, so invalid status raises immediately
    from domain.exceptions import ValidationError
    
    # This tests that validation is enforced at domain layer (during Table creation)
    with pytest.raises(ValidationError, match="status must be one of"):
        Table(number=99, capacity=4, zone="INVALID", features={}, status="invalid_status")


def test_table_repository_add_appears_in_list(app, repo):
    """Test that added table appears in list() (persistence verification)."""
    new_table = Table(number=50, capacity=2, zone="TEST_ZONE", features={}, status="available")
    added_table = repo.add(new_table)
    
    # Verify added table is in list
    tables = repo.list()
    found = any(t.id == added_table.id for t in tables)
    assert found, f"Added table (ID: {added_table.id}) not found in repo.list()"


def test_table_repository_delete_idempotency(app, repo):
    """Test that deleting twice raises error (not idempotent - correct behavior)."""
    new_table = Table(number=51, capacity=4, zone="DELETE_TEST", features={}, status="available")
    added_table = repo.add(new_table)
    
    # First delete succeeds
    repo.delete(added_table.id)
    
    # Second delete should raise error - table doesn't exist
    with pytest.raises(ValueError, match="does not exist"):
        repo.delete(added_table.id)


def test_table_repository_features_with_empty_dict(app, repo):
    """Test that tables with empty features dict are handled correctly."""
    new_table = Table(number=52, capacity=4, zone="EMPTY_FEATURES", features={}, status="available")
    added_table = repo.add(new_table)
    
    retrieved = repo.get_by_id(added_table.id)
    assert retrieved is not None
    assert retrieved.features == {}, f"Empty dict not preserved: got {retrieved.features}"


def test_table_repository_features_with_none(app, repo):
    """Test that tables with None features are handled correctly."""
    new_table = Table(number=53, capacity=4, zone="NONE_FEATURES", features=None, status="available")
    added_table = repo.add(new_table)
    
    retrieved = repo.get_by_id(added_table.id)
    assert retrieved is not None
    # Features can be None or empty dict - verify it's one of these
    assert retrieved.features is None or retrieved.features == {}, \
        f"None features not preserved properly: got {retrieved.features}"