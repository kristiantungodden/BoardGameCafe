import pytest

from shared.domain.exceptions import ValidationError
from features.tables.domain.models.table import Table, VALID_TABLE_STATUSES


def test_table_creation_uses_expected_defaults():
    table = Table(number=1, capacity=4)

    assert table.number == 1
    assert table.capacity == 4
    assert table.floor == 1
    assert table.status == "available"


def test_table_number_must_be_positive():
    with pytest.raises(ValidationError, match="number must be a positive integer"):
        Table(number=0, capacity=4)


def test_table_capacity_must_be_positive():
    with pytest.raises(ValidationError, match="capacity must be a positive integer"):
        Table(number=1, capacity=0)


def test_table_floor_must_be_positive():
    with pytest.raises(ValidationError, match="floor must be a positive integer"):
        Table(number=1, capacity=4, floor=0)


def test_table_status_must_be_known_value():
    with pytest.raises(ValidationError) as exc_info:
        Table(number=1, capacity=4, status="abcd")

    expected_statuses = ", ".join(sorted(VALID_TABLE_STATUSES))
    assert str(exc_info.value) == f"status must be one of: {expected_statuses}"


class TestTableEdgeCases:
    """Test suite for Table edge cases and boundary conditions."""
    
    def test_table_accepts_various_valid_prices(self):
        """RULE: Table accepts various valid price values."""
        # Zero price (free table)
        table = Table(number=1, capacity=4, price_cents=0)
        assert table.price_cents == 0
        
        # Large price
        table = Table(number=1, capacity=4, price_cents=1000000)
        assert table.price_cents == 1000000
    
    def test_table_rejects_negative_price(self):
        """RULE: price_cents must be non-negative."""
        with pytest.raises(ValidationError, match="price_cents must be a non-negative integer"):
            Table(number=1, capacity=4, price_cents=-1)
    
    def test_table_accepts_various_valid_capacities(self):
        """RULE: Table accepts various valid capacity values."""
        # Small capacity
        table = Table(number=1, capacity=1)
        assert table.capacity == 1
        
        # Large capacity
        table = Table(number=1, capacity=50)
        assert table.capacity == 50
    
    def test_table_accepts_various_valid_floors(self):
        """RULE: Table accepts various valid floor values."""
        # First floor
        table = Table(number=1, capacity=4, floor=1)
        assert table.floor == 1
        
        # High floor
        table = Table(number=1, capacity=4, floor=10)
        assert table.floor == 10
    
    def test_table_accepts_optional_features(self):
        """RULE: Table can have optional features dictionary."""
        table = Table(
            number=1,
            capacity=4,
            features={"window_seat": True, "outdoor": False},
        )
        assert table.features == {"window_seat": True, "outdoor": False}
    
    def test_table_accepts_optional_dimensions(self):
        """RULE: Table can have optional width, height, and rotation."""
        table = Table(
            number=1,
            capacity=4,
            width=120,
            height=80,
            rotation=45,
        )
        assert table.width == 120
        assert table.height == 80
        assert table.rotation == 45
    
    def test_table_rejects_negative_width(self):
        """RULE: width must be a positive integer if provided."""
        with pytest.raises(ValidationError, match="width must be a positive integer"):
            Table(number=1, capacity=4, width=-10)
    
    def test_table_rejects_negative_height(self):
        """RULE: height must be a positive integer if provided."""
        with pytest.raises(ValidationError, match="height must be a positive integer"):
            Table(number=1, capacity=4, height=-10)
    
    def test_table_rejects_negative_rotation(self):
        """RULE: rotation must be a non-negative integer if provided."""
        with pytest.raises(ValidationError, match="rotation must be a non-negative integer"):
            Table(number=1, capacity=4, rotation=-1)
    
    def test_table_accepts_zero_rotation(self):
        """RULE: rotation can be zero."""
        table = Table(number=1, capacity=4, rotation=0)
        assert table.rotation == 0
    
    def test_table_rejects_non_integer_values(self):
        """RULE: Integer fields must be actual integers."""
        with pytest.raises(ValidationError):
            Table(number=1.5, capacity=4)
        
        with pytest.raises(ValidationError):
            Table(number=1, capacity=4.5)
        
        with pytest.raises(ValidationError):
            Table(number=1, capacity=4, floor=1.5)
        
        with pytest.raises(ValidationError):
            Table(number=1, capacity=4, width=100.5)
    
    def test_table_accepts_optional_zone(self):
        """RULE: Table can have optional zone."""
        table = Table(
            number=1,
            capacity=4,
            zone="Window Section",
        )
        assert table.zone == "Window Section"
        
        # None zone is also valid
        table = Table(
            number=1,
            capacity=4,
            zone=None,
        )
        assert table.zone is None
    
    def test_table_default_values(self):
        """RULE: Table has sensible default values."""
        table = Table(number=1, capacity=4)
        
        assert table.price_cents == 15000
        assert table.floor == 1
        assert table.zone is None
        assert table.features is None
        assert table.width is None
        assert table.height is None
        assert table.rotation is None
        assert table.status == "available"
