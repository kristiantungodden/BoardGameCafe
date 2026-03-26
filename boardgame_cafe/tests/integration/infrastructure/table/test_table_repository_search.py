"""Search and filter tests for TableRepository."""
from domain.models.table import Table
from infrastructure.repositories import TableFilters

import pytest
from conftest import seed_tables


def test_table_repository_search_filters_zone(app, repo):
    """Test filtering by zone."""
    table1 = Table(number=7, capacity=4, zone="G", features={"near_window": True}, status="available")
    table2 = Table(number=8, capacity=4, zone="H", features={"near_window": False}, status="available")
    table3 = Table(number=9, capacity=4, zone="G", features={"near_window": False}, status="available")
    repo.add(table1)
    repo.add(table2)
    repo.add(table3)

    filters = TableFilters(zone="G")
    filtered_tables = repo.search(filters)
    
    assert len(filtered_tables) == 2
    assert all(t.zone == "G" for t in filtered_tables)


def test_table_repository_search_filters_status(app, repo):
    """Test filtering by status."""
    seed_tables(repo)
    
    filtered_tables = repo.search(TableFilters(status="available"))
    
    assert len(filtered_tables) == 2
    assert all(t.status == "available" for t in filtered_tables)


def test_table_repository_search_filters_min_capacity(app, repo):
    """Test filtering by minimum capacity."""
    seed_tables(repo)
    
    filtered_tables = repo.search(TableFilters(min_capacity=5))
    
    assert {t.number for t in filtered_tables} == {3, 4}


def test_table_repository_search_filters_max_capacity(app, repo):
    """Test filtering by maximum capacity."""
    seed_tables(repo)
    
    filtered_tables = repo.search(TableFilters(max_capacity=4))
    
    assert {t.number for t in filtered_tables} == {1, 2, 5}


def test_table_repository_search_filters_feature_true(app, repo):
    """Test filtering by presence of a feature."""
    seed_tables(repo)
    
    filtered_tables = repo.search(TableFilters(feature="near_window"))
    
    assert {t.number for t in filtered_tables} == {1, 3}


def test_table_repository_search_filters_is_available_true(app, repo):
    """Test filtering for available tables only."""
    seed_tables(repo)
    
    filtered_tables = repo.search(TableFilters(is_available=True))
    
    assert len(filtered_tables) == 2
    assert all(t.status == "available" for t in filtered_tables)


def test_table_repository_search_filters_is_available_false(app, repo):
    """Test filtering for non-available tables (occupied, reserved, maintenance)."""
    seed_tables(repo)
    
    filtered_tables = repo.search(TableFilters(is_available=False))
    
    assert len(filtered_tables) == 3
    assert {t.status for t in filtered_tables} == {"occupied", "reserved", "maintenance"}
    assert {t.number for t in filtered_tables} == {2, 4, 5}


def test_table_repository_search_combines_multiple_filters(app, repo):
    """Test combining multiple filters (AND logic) - basic combination."""
    seed_tables(repo)
    
    filtered_tables = repo.search(
        TableFilters(zone="B", min_capacity=5, status="available")
    )
    
    assert len(filtered_tables) == 1
    assert filtered_tables[0].number == 3
    # Verify all filter conditions met
    assert filtered_tables[0].zone == "B"
    assert filtered_tables[0].capacity >= 5
    assert filtered_tables[0].status == "available"


def test_table_repository_search_empty_filters_returns_all(app, repo):
    """Test that empty filters return all tables."""
    seed_tables(repo)
    
    filtered_tables = repo.search(TableFilters())
    
    assert len(filtered_tables) == 5


def test_table_repository_search_with_no_matches_returns_empty_list(app, repo):
    """Test that search with impossible filters returns empty list."""
    seed_tables(repo)
    
    # Zone that doesn't exist in seed data
    filters = TableFilters(zone="Z")
    result = repo.search(filters)
    
    assert result == []
    assert isinstance(result, list)


def test_table_repository_search_with_contradictory_filters_returns_empty_list(app, repo):
    """Test that search with contradictory filters (is_available=True + status='occupied') returns empty list."""
    seed_tables(repo)
    
    # These filters contradict each other: is_available=True means status must be "available"
    # but we're also requiring status="occupied"
    filters = TableFilters(is_available=True, status="occupied")
    result = repo.search(filters)
    
    assert result == []


def test_table_repository_search_with_missing_feature_key_excludes_table(app, repo):
    """Test that search for a feature on tables without that key safely excludes them."""
    seed_tables(repo)
    
    # Search for feature "inexistent_feature" which no table has
    filters = TableFilters(feature="inexistent_feature")
    result = repo.search(filters)
    
    assert result == []


def test_table_repository_search_count_by_status_on_empty_tables_returns_all_statuses_zero(app, repo):
    """Test that count_by_status on empty table set returns all statuses with count 0."""
    # Don't seed any tables - db is already clean from autouse fixture
    counts = repo.count_by_status()
    
    # Must return a dict with all known statuses set to 0
    # This catches bugs where implementation might omit statuses or return incomplete dict
    assert isinstance(counts, dict), f"count_by_status() must return dict, got {type(counts)}"
    
    # Verify all valid statuses are present in the result
    expected_statuses = {"available", "occupied", "reserved", "maintenance"}
    for status in expected_statuses:
        assert status in counts, f"Status '{status}' missing from count_by_status() result"
        assert counts[status] == 0, f"Status '{status}' should be 0, got {counts[status]}"


def test_table_repository_search_with_min_and_max_capacity_filters(app, repo):
    """Test that capacity range constraints work correctly."""
    seed_tables(repo)
    
    # Search for tables with capacity between 4 and 6 (inclusive)
    filters = TableFilters(min_capacity=4, max_capacity=6)
    result = repo.search(filters)
    
    # Should return tables 2 (cap=4), 3 (cap=6), and 5 (cap=4)
    assert len(result) == 3
    assert {t.number for t in result} == {2, 3, 5}
    assert all(4 <= t.capacity <= 6 for t in result)


def test_table_repository_search_with_status_and_is_available_consistency(app, repo):
    """Test that status-based and is_available-based filtering are consistent."""
    seed_tables(repo)
    
    # Get all available tables via is_available filter
    available_via_flag = repo.search(TableFilters(is_available=True))
    
    # Get all available tables via status filter
    available_via_status = repo.search(TableFilters(status="available"))
    
    # Should be identical
    assert {t.id for t in available_via_flag} == {t.id for t in available_via_status}


def test_table_repository_search_with_zone_and_capacity_combined(app, repo):
    """Test that multiple independent filters combine correctly (AND logic)."""
    seed_tables(repo)
    
    # Zone B tables: 3 (cap=6, available), 4 (cap=8, maintenance)
    # Zone B + min_capacity=6: should get 3 and 4
    filters = TableFilters(zone="B", min_capacity=6)
    result = repo.search(filters)
    
    assert len(result) == 2
    assert {t.number for t in result} == {3, 4}
    assert all(t.zone == "B" and t.capacity >= 6 for t in result)


def test_table_repository_search_filter_isolation_zone_impossible(app, repo):
    """Test that impossible filter returns empty even when other conditions would match."""
    seed_tables(repo)
    
    # Zone "NONEXISTENT" should return empty, regardless of other filters
    # If zone filter is broken, might return all available tables
    filters = TableFilters(zone="NONEXISTENT", status="available")
    result = repo.search(filters)
    
    assert result == [], f"Impossible zone filter should return empty, got {len(result)} results"


def test_table_repository_search_filter_isolation_status_impossible(app, repo):
    """Test that impossible status filter returns empty even when other filters would match."""
    seed_tables(repo)
    
    # Nonexistent status should return empty
    # If status filter is broken, might return all tables from matching zone
    filters = TableFilters(zone="A", status="nonexistent_status")
    result = repo.search(filters)
    
    assert result == [], f"Impossible status filter should return empty, got {len(result)} results"


def test_table_repository_search_boundary_min_capacity_exact_match(app, repo):
    """Test min_capacity with exact match (catches >= vs > bugs)."""
    seed_tables(repo)
    
    # Seed has capacities: 2, 4, 6, 8, 4
    # min_capacity=4 should return tables with capacity >= 4: {2, 4, 6, 8, 4}
    # But not with capacity > 4 (that would miss capacity=4 tables)
    filters = TableFilters(min_capacity=4)
    result = repo.search(filters)
    
    # Tables 2 (cap=4), 3 (cap=6), 4 (cap=8), 5 (cap=4)
    assert {t.number for t in result} == {2, 3, 4, 5}, \
        f"min_capacity=4 should include tables with exactly capacity 4"


def test_table_repository_search_boundary_max_capacity_exact_match(app, repo):
    """Test max_capacity with exact match (catches <= vs < bugs)."""
    seed_tables(repo)
    
    # max_capacity=6 should return tables with capacity <= 6: {2, 4, 6, 4}
    # But not with capacity < 6 (that would miss capacity=6 table)
    filters = TableFilters(max_capacity=6)
    result = repo.search(filters)
    
    # Tables 1 (cap=2), 2 (cap=4), 3 (cap=6), 5 (cap=4)
    assert {t.number for t in result} == {1, 2, 3, 5}, \
        f"max_capacity=6 should include tables with exactly capacity 6"


def test_table_repository_search_capacity_range_both_boundaries(app, repo):
    """Test capacity range with both min and max at boundaries (catches off-by-one bugs)."""
    seed_tables(repo)
    
    # min_capacity=4, max_capacity=6 should return capacity in [4, 6]: {2, 3, 5}
    filters = TableFilters(min_capacity=4, max_capacity=6)
    result = repo.search(filters)
    
    # Tables 2 (cap=4), 3 (cap=6), 5 (cap=4)
    assert {t.number for t in result} == {2, 3, 5}
    assert all(4 <= t.capacity <= 6 for t in result)


def test_table_repository_search_three_filter_combination(app, repo):
    """Test combining three filters - zone + status + capacity."""
    seed_tables(repo)
    
    # Zone A: tables 1, 2
    # Status available: tables 1, 3
    # Capacity <= 4: tables 1, 2, 5
    # All three: only table 1 (zone A, available, capacity 2)
    filters = TableFilters(zone="A", status="available", min_capacity=2, max_capacity=4)
    result = repo.search(filters)
    
    assert len(result) == 1
    assert result[0].number == 1
    assert result[0].zone == "A"
    assert result[0].status == "available"
    assert result[0].capacity == 2


def test_table_repository_search_feature_filter_with_tables_missing_feature(app, repo):
    """Test feature filter when some tables have feature and others don't."""
    seed_tables(repo)
    
    # Search for "near_window"
    # Tables 1, 3 have near_window=True
    # Tables 2, 4, 5 have near_window=False (explicitly set to False, not missing)
    filters = TableFilters(feature="near_window")
    result = repo.search(filters)
    
    assert len(result) == 2, f"Should find exactly 2 tables with near_window, got {len(result)}"
    assert {t.number for t in result} == {1, 3}
    # Verify all returned tables have the feature as True
    assert all(t.features.get("near_window") is True for t in result)


def test_table_repository_search_feature_filter_with_tables_having_empty_features(app, repo):
    """Test feature filter safely handles tables with None or empty features dict."""
    # Add a table with empty features
    table_empty = Table(number=100, capacity=4, zone="TEST", features={}, status="available")
    repo.add(table_empty)
    
    # Add a table with None features
    table_none = Table(number=101, capacity=4, zone="TEST", features=None, status="available")
    repo.add(table_none)
    
    # Search for a feature - should not crash and should not return these tables
    filters = TableFilters(feature="anything")
    result = repo.search(filters)
    
    # Should not crash and should not include the tables with empty/None features
    assert not any(t.number in {100, 101} for t in result), \
        "Feature filter should exclude tables with empty/None features"


def test_table_repository_search_multiple_combinations_for_and_logic(app, repo):
    """Test that filters truly use AND logic by checking multiple combinations."""
    seed_tables(repo)
    
    # Combination 1: zone A + available = tables 1
    result1 = repo.search(TableFilters(zone="A", status="available"))
    assert {t.number for t in result1} == {1}
    
    # Combination 2: zone A + occupied = table 2
    result2 = repo.search(TableFilters(zone="A", status="occupied"))
    assert {t.number for t in result2} == {2}
    
    # Combination 3: zone B + available = table 3
    result3 = repo.search(TableFilters(zone="B", status="available"))
    assert {t.number for t in result3} == {3}
    
    # Combination 4: zone B + maintenance = table 4
    result4 = repo.search(TableFilters(zone="B", status="maintenance"))
    assert {t.number for t in result4} == {4}
    
    # The key test: if any filter breaks, at least one combination will fail
    # This catches bugs where one filter "overwrites" another
