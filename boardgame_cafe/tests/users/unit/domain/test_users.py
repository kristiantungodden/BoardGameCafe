# Tests for the core User domain model.

import pytest
from features.users.domain.models.user import User, Role
from shared.domain.exceptions import ValidationError


class TestUserCreation:
    """Test basic User entity creation."""

    def test_user_creation_with_valid_data(self):
        """Test creating a user with valid data."""
        user = User("John Doe", "john@test.com", "hash123")

        assert user.name == "John Doe"
        assert user.email == "john@test.com"
        assert user.password_hash == "hash123"
        assert user.role == Role.CUSTOMER
        assert user.force_password_change is False
        assert user.phone is None
        assert user.id is None

    def test_user_creation_with_all_fields(self):
        """Test creating a user with all optional fields."""
        user = User(
            name="Jane Smith",
            email="jane@test.com",
            password_hash="hash456",
            role=Role.STAFF,
            force_password_change=True,
            phone="12345678",
            id=42
        )

        assert user.name == "Jane Smith"
        assert user.email == "jane@test.com"
        assert user.password_hash == "hash456"
        assert user.role == Role.STAFF
        assert user.force_password_change is True
        assert user.phone == "12345678"
        assert user.id == 42


class TestUserValidation:
    """Test basic User validation."""

    def test_valid_user_passes_validation(self):
        """Test that valid user data passes validation."""
        user = User("Valid User", "valid@test.com", "hash123")
        assert user.name == "Valid User"

    def test_empty_name_raises_validation_error(self):
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError, match="Name cannot be empty"):
            User("", "test@test.com", "hash123")

    def test_invalid_email_raises_validation_error(self):
        """Test that invalid email raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid email address"):
            User("Test User", "invalid-email", "hash123")

    def test_empty_password_hash_raises_validation_error(self):
        """Test that empty password hash raises ValidationError."""
        with pytest.raises(ValidationError, match="Password hash cannot be empty"):
            User("Test User", "test@test.com", "")


class TestUserBusinessMethods:
    """Test core User business methods."""

    def test_change_password_updates_hash_and_resets_force_change(self):
        """Test that change_password updates hash and resets force change flag."""
        user = User("Test", "test@test.com", "old_hash", force_password_change=True)

        user.change_password("new_hash123")

        assert user.password_hash == "new_hash123"
        assert user.force_password_change is False

    def test_force_password_reset_sets_flag(self):
        """Test that force_password_reset sets the force change flag."""
        user = User("Test", "test@test.com", "hash123", force_password_change=False)

        user.force_password_reset()

        assert user.force_password_change is True

    def test_update_profile_with_name_and_phone(self):
        """Test updating both name and phone in profile."""
        user = User("Old Name", "test@test.com", "hash123", phone="123")

        user.update_profile(name="New Name", phone="456")

        assert user.name == "New Name"
        assert user.phone == "456"

    def test_update_profile_revalidates_data(self):
        """Test that update_profile revalidates the data."""
        user = User("Valid Name", "test@test.com", "hash123")

        with pytest.raises(ValidationError, match="Name cannot be empty"):
            user.update_profile(name="")


class TestUserRoleMethods:
    """Test User role checking methods."""

    def test_role_methods_work_correctly(self):
        """Test that role checking methods work for all roles."""
        customer = User("Cust", "c@test.com", "h", Role.CUSTOMER)
        staff = User("Staff", "s@test.com", "h", Role.STAFF)
        admin = User("Admin", "a@test.com", "h", Role.ADMIN)

        # Customer checks
        assert customer.is_customer()
        assert not customer.is_staff()
        assert not customer.is_admin()

        # Staff checks
        assert not staff.is_customer()
        assert staff.is_staff()
        assert not staff.is_admin()

        # Admin checks
        assert not admin.is_customer()
        assert not admin.is_staff()
        assert admin.is_admin()

    def test_can_access_admin_features(self):
        """Test admin feature access for different roles."""
        customer = User("Cust", "c@test.com", "h", Role.CUSTOMER)
        staff = User("Staff", "s@test.com", "h", Role.STAFF)
        admin = User("Admin", "a@test.com", "h", Role.ADMIN)

        assert not customer.can_access_admin_features()
        assert staff.can_access_admin_features()
        assert admin.can_access_admin_features()