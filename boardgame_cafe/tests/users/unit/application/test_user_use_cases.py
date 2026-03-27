# Tests for user use cases.

import pytest
from unittest.mock import Mock

from features.users.domain.models.user import User, Role
from shared.domain.exceptions import ValidationError
from features.users.application.use_cases.user_use_cases import (
    CreateUserUseCase,
    UpdateUserUseCase,
    ChangePasswordUseCase,
    CreateUserCommand,
    UpdateUserCommand,
    ChangePasswordCommand,
)


class TestCreateUserUseCase:
    """Test CreateUserUseCase."""

    def test_create_user_with_valid_command(self):
        """Test creating a user with valid command data."""
        use_case = CreateUserUseCase()

        cmd = CreateUserCommand(
            name="John Doe",
            email="john.doe@example.com",
            password_hash="hashed_password_123",
            role=Role.STAFF,
            phone="+47 123 45 678"
        )

        user = use_case.execute(cmd)

        assert user.name == "John Doe"
        assert user.email == "john.doe@example.com"
        assert user.password_hash == "hashed_password_123"
        assert user.role == Role.STAFF
        assert user.phone == "+47 123 45 678"
        assert user.force_password_change is False
        assert user.id is None

    def test_create_user_with_defaults(self):
        """Test creating a user with default values."""
        use_case = CreateUserUseCase()

        cmd = CreateUserCommand(
            name="Jane Smith",
            email="jane.smith@example.com",
            password_hash="hashed_password_456"
        )

        user = use_case.execute(cmd)

        assert user.name == "Jane Smith"
        assert user.email == "jane.smith@example.com"
        assert user.password_hash == "hashed_password_456"
        assert user.role == Role.CUSTOMER
        assert user.phone is None


class TestUpdateUserUseCase:
    """Test UpdateUserUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repo = Mock()
        self.use_case = UpdateUserUseCase(self.mock_repo)

    def test_update_user_profile_success(self):
        """Test successful profile update."""
        requesting_user = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        target_user = User("Old Name", "target@test.com", "hash", Role.CUSTOMER, phone="123", id=2)

        self.mock_repo.get_by_id.return_value = target_user
        self.mock_repo.save.return_value = target_user

        cmd = UpdateUserCommand(
            user_id=2,
            name="New Name",
            phone="456"
        )

        result = self.use_case.execute(cmd, requesting_user)

        assert result.name == "New Name"
        assert result.phone == "456"
        assert result.email == "target@test.com"  # Unchanged
        self.mock_repo.save.assert_called_once_with(target_user)

    def test_update_user_role_success(self):
        """Test successful role update."""
        requesting_user = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        target_user = User("User", "target@test.com", "hash", Role.CUSTOMER, id=2)

        self.mock_repo.get_by_id.return_value = target_user
        self.mock_repo.save.return_value = target_user

        cmd = UpdateUserCommand(
            user_id=2,
            role=Role.STAFF
        )

        result = self.use_case.execute(cmd, requesting_user)

        assert result.role == Role.STAFF
        self.mock_repo.save.assert_called_once_with(target_user)

    def test_update_user_not_found(self):
        """Test updating non-existent user."""
        requesting_user = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)

        self.mock_repo.get_by_id.return_value = None

        cmd = UpdateUserCommand(user_id=999, name="New Name")

        with pytest.raises(ValidationError, match="User not found"):
            self.use_case.execute(cmd, requesting_user)

    def test_update_user_insufficient_permissions(self):
        """Test updating user without sufficient permissions."""
        requesting_user = User("Staff", "staff@test.com", "hash", Role.STAFF, id=1)
        target_user = User("Other Staff", "other@test.com", "hash", Role.STAFF, id=2)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = UpdateUserCommand(user_id=2, name="New Name")

        with pytest.raises(ValidationError, match="Insufficient permissions to update user"):
            self.use_case.execute(cmd, requesting_user)

    def test_update_user_invalid_role_transition(self):
        """Test updating user with invalid role transition."""
        requesting_user = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        target_user = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = UpdateUserCommand(user_id=2, role=Role.CUSTOMER)  # Staff cannot be demoted

        with pytest.raises(ValidationError, match="Invalid role transition"):
            self.use_case.execute(cmd, requesting_user)


class TestChangePasswordUseCase:
    """Test ChangePasswordUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repo = Mock()
        self.use_case = ChangePasswordUseCase(self.mock_repo)

    def test_change_own_password_success(self):
        """Test user successfully changing their own password."""
        user = User("User", "user@test.com", "old_hash", Role.CUSTOMER, id=1)

        self.mock_repo.get_by_id.return_value = user
        self.mock_repo.save.return_value = user

        cmd = ChangePasswordCommand(user_id=1, new_password_hash="new_hash123")

        result = self.use_case.execute(cmd, user)

        assert result.password_hash == "new_hash123"
        assert result.force_password_change is False
        self.mock_repo.save.assert_called_once_with(user)

    def test_admin_change_other_password_success(self):
        """Test admin successfully changing another user's password."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        target_user = User("User", "user@test.com", "old_hash", Role.CUSTOMER, id=2)

        self.mock_repo.get_by_id.return_value = target_user
        self.mock_repo.save.return_value = target_user

        cmd = ChangePasswordCommand(user_id=2, new_password_hash="new_hash123")

        result = self.use_case.execute(cmd, admin)

        assert result.password_hash == "new_hash123"
        assert result.force_password_change is False
        self.mock_repo.save.assert_called_once_with(target_user)

    def test_change_password_user_not_found(self):
        """Test changing password for non-existent user."""
        requesting_user = User("User", "user@test.com", "hash", Role.CUSTOMER, id=1)

        self.mock_repo.get_by_id.return_value = None

        cmd = ChangePasswordCommand(user_id=999, new_password_hash="new_hash")

        with pytest.raises(ValidationError, match="User not found"):
            self.use_case.execute(cmd, requesting_user)

    def test_change_password_insufficient_permissions(self):
        """Test changing password without sufficient permissions."""
        requesting_user = User("Staff", "staff@test.com", "hash", Role.STAFF, id=1)
        target_user = User("Other Staff", "other@test.com", "hash", Role.STAFF, id=2)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = ChangePasswordCommand(user_id=2, new_password_hash="new_hash")

        with pytest.raises(ValidationError, match="Insufficient permissions to change password"):
            self.use_case.execute(cmd, requesting_user)