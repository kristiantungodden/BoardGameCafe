# Tests for user use cases.

import pytest
from unittest.mock import Mock

from features.users.domain.models.user import User, Role
from shared.domain.exceptions import ValidationError
from features.users.application.use_cases.user_use_cases import (
    CreateUserUseCase,
    UpdateUserUseCase,
    UpdateOwnProfileUseCase,
    ChangePasswordUseCase,
    CreateStewardUseCase,
    ListUsersUseCase,
    ForcePasswordResetUseCase,
    CreateUserCommand,
    UpdateUserCommand,
    UpdateOwnProfileCommand,
    ChangePasswordCommand,
    CreateStewardCommand,
    ListUsersQuery,
    ForcePasswordResetCommand,
)


class TestCreateUserUseCase:
    """Test CreateUserUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repo = Mock()
        self.mock_repo.save.side_effect = lambda user: user
        self.use_case = CreateUserUseCase(self.mock_repo)

    def test_create_user_with_valid_command(self):
        """Test creating a user with valid command data."""
        cmd = CreateUserCommand(
            name="John Doe",
            email="john.doe@example.com",
            password_hash="hashed_password_123",
            role=Role.STAFF,
            phone="+47 123 45 678"
        )

        user = self.use_case.execute(cmd)

        assert user.name == "John Doe"
        assert user.email == "john.doe@example.com"
        assert user.password_hash == "hashed_password_123"
        assert user.role == Role.STAFF
        assert user.phone == "+47 123 45 678"
        assert user.force_password_change is False
        self.mock_repo.save.assert_called_once()

    def test_create_user_with_defaults(self):
        """Test creating a user with default values."""
        cmd = CreateUserCommand(
            name="Jane Smith",
            email="jane.smith@example.com",
            password_hash="hashed_password_456"
        )

        user = self.use_case.execute(cmd)

        assert user.name == "Jane Smith"
        assert user.email == "jane.smith@example.com"
        assert user.password_hash == "hashed_password_456"
        assert user.role == Role.CUSTOMER
        assert user.phone is None
        self.mock_repo.save.assert_called_once()

    def test_create_user_persists_to_repository(self):
        """Test that created user is saved to repository."""
        cmd = CreateUserCommand(
            name="Test User",
            email="test@example.com",
            password_hash="hash123"
        )

        self.use_case.execute(cmd)

        # Verify save was called with a User object
        self.mock_repo.save.assert_called_once()
        saved_user = self.mock_repo.save.call_args[0][0]
        assert isinstance(saved_user, User)
        assert saved_user.name == "Test User"
        assert saved_user.email == "test@example.com"

    def test_create_user_domain_validation_error(self):
        """Test that invalid user data raises ValidationError."""
        cmd = CreateUserCommand(
            name="",  # Invalid: empty name
            email="test@example.com",
            password_hash="hash123"
        )

        with pytest.raises(ValidationError, match="Name cannot be empty"):
            self.use_case.execute(cmd)
        self.mock_repo.save.assert_not_called()


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
        self.mock_repo.save.assert_not_called()

    def test_update_user_insufficient_permissions(self):
        """Test updating user without sufficient permissions."""
        requesting_user = User("Staff", "staff@test.com", "hash", Role.STAFF, id=1)
        target_user = User("Other Staff", "other@test.com", "hash", Role.STAFF, id=2)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = UpdateUserCommand(user_id=2, name="New Name")

        with pytest.raises(ValidationError, match="Insufficient permissions to update user"):
            self.use_case.execute(cmd, requesting_user)
        self.mock_repo.save.assert_not_called()

    def test_update_user_invalid_role_transition(self):
        """Test updating user with invalid role transition."""
        requesting_user = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        target_user = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = UpdateUserCommand(user_id=2, role=Role.CUSTOMER)  # Staff cannot be demoted

        with pytest.raises(ValidationError, match="Invalid role transition"):
            self.use_case.execute(cmd, requesting_user)
        self.mock_repo.save.assert_not_called()

    def test_update_user_failed_profile_validation_does_not_mutate_role(self):
        """If update fails validation, target role should remain unchanged and not persist."""
        requesting_user = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        target_user = User("Target", "target@test.com", "hash", Role.CUSTOMER, id=2)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = UpdateUserCommand(
            user_id=2,
            role=Role.STAFF,
            name="",  # Invalid profile update
        )

        with pytest.raises(ValidationError, match="Name cannot be empty"):
            self.use_case.execute(cmd, requesting_user)

        assert target_user.role == Role.CUSTOMER
        self.mock_repo.save.assert_not_called()


class TestUpdateOwnProfileUseCase:
    """Test UpdateOwnProfileUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repo = Mock()
        self.use_case = UpdateOwnProfileUseCase(self.mock_repo)

    def test_update_own_profile_success(self):
        """Test successful self-service profile update."""
        requesting_user = User("User", "user@test.com", "hash", Role.CUSTOMER, id=1)
        target_user = User("Old Name", "user@test.com", "hash", Role.CUSTOMER, phone="123", id=1)

        self.mock_repo.get_by_id.return_value = target_user
        self.mock_repo.save.return_value = target_user

        cmd = UpdateOwnProfileCommand(user_id=1, name="New Name", phone="456")

        result = self.use_case.execute(cmd, requesting_user)

        assert result.name == "New Name"
        assert result.phone == "456"
        self.mock_repo.save.assert_called_once_with(target_user)

    def test_update_own_profile_rejects_other_user(self):
        """Users should not be able to update someone else's profile."""
        requesting_user = User("User", "user@test.com", "hash", Role.CUSTOMER, id=1)
        target_user = User("Other", "other@test.com", "hash", Role.CUSTOMER, id=2)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = UpdateOwnProfileCommand(user_id=2, name="Hacker Name")

        with pytest.raises(ValidationError, match="Users can only update their own profile"):
            self.use_case.execute(cmd, requesting_user)

        self.mock_repo.save.assert_not_called()

    def test_update_own_profile_validation_error_does_not_persist(self):
        """Invalid profile updates should not be persisted."""
        requesting_user = User("User", "user@test.com", "hash", Role.CUSTOMER, id=1)
        target_user = User("Old Name", "user@test.com", "hash", Role.CUSTOMER, phone="123", id=1)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = UpdateOwnProfileCommand(user_id=1, name="")

        with pytest.raises(ValidationError, match="Name cannot be empty"):
            self.use_case.execute(cmd, requesting_user)

        assert target_user.name == "Old Name"
        assert target_user.phone == "123"
        self.mock_repo.save.assert_not_called()


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
        self.mock_repo.save.assert_not_called()

    def test_change_password_insufficient_permissions(self):
        """Test changing password without sufficient permissions."""
        requesting_user = User("Staff", "staff@test.com", "hash", Role.STAFF, id=1)
        target_user = User("Other Staff", "other@test.com", "hash", Role.STAFF, id=2)

        self.mock_repo.get_by_id.return_value = target_user

        cmd = ChangePasswordCommand(user_id=2, new_password_hash="new_hash")

        with pytest.raises(ValidationError, match="Insufficient permissions to change password"):
            self.use_case.execute(cmd, requesting_user)
        self.mock_repo.save.assert_not_called()


class TestCreateStewardUseCase:
    """Test CreateStewardUseCase."""

    def setup_method(self):
        self.mock_repo = Mock()
        self.use_case = CreateStewardUseCase(self.mock_repo)

    def test_admin_can_create_steward_with_forced_password_change(self):
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        self.mock_repo.get_by_email.return_value = None
        self.mock_repo.save.side_effect = lambda user: user

        cmd = CreateStewardCommand(
            name="New Steward",
            email="steward@test.com",
            password_hash="hashed_pw",
            phone="12345678",
        )

        user = self.use_case.execute(cmd, admin)

        assert user.role == Role.STAFF
        assert user.force_password_change is True
        self.mock_repo.save.assert_called_once()

    def test_non_admin_cannot_create_steward(self):
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)
        cmd = CreateStewardCommand(
            name="New Steward",
            email="steward@test.com",
            password_hash="hashed_pw",
        )

        with pytest.raises(ValidationError, match="Admin access required"):
            self.use_case.execute(cmd, staff)

        self.mock_repo.save.assert_not_called()

    def test_create_steward_rejects_duplicate_email(self):
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        existing = User("Existing", "steward@test.com", "hash", Role.STAFF, id=3)
        self.mock_repo.get_by_email.return_value = existing

        cmd = CreateStewardCommand(
            name="New Steward",
            email="steward@test.com",
            password_hash="hashed_pw",
        )

        with pytest.raises(ValidationError, match="email already exists"):
            self.use_case.execute(cmd, admin)

        self.mock_repo.save.assert_not_called()


class TestListUsersUseCase:
    """Test ListUsersUseCase."""

    def setup_method(self):
        self.mock_repo = Mock()
        self.use_case = ListUsersUseCase(self.mock_repo)

    def test_list_users_for_admin(self):
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        users = [
            User("Alice", "alice@test.com", "hash", Role.CUSTOMER, id=2),
            User("Bob", "bob@test.com", "hash", Role.STAFF, id=3),
        ]
        self.mock_repo.list_all.return_value = users

        result = self.use_case.execute(ListUsersQuery(), admin)

        assert len(result) == 2
        self.mock_repo.list_all.assert_called_once()

    def test_list_users_with_search_filter(self):
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        users = [
            User("Alice", "alice@test.com", "hash", Role.CUSTOMER, id=2),
            User("Bob", "bob@example.com", "hash", Role.STAFF, id=3),
        ]
        self.mock_repo.list_all.return_value = users

        result = self.use_case.execute(ListUsersQuery(search_text="example"), admin)

        assert len(result) == 1
        assert result[0].email == "bob@example.com"

    def test_list_users_rejects_customer(self):
        customer = User("Customer", "c@test.com", "hash", Role.CUSTOMER, id=4)

        with pytest.raises(ValidationError, match="Insufficient permissions to list users"):
            self.use_case.execute(ListUsersQuery(), customer)


class TestForcePasswordResetUseCase:
    """Test ForcePasswordResetUseCase."""

    def setup_method(self):
        self.mock_repo = Mock()
        self.use_case = ForcePasswordResetUseCase(self.mock_repo)

    def test_admin_can_force_reset_customer(self):
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        target = User("Customer", "cust@test.com", "hash", Role.CUSTOMER, id=2)

        self.mock_repo.get_by_id.return_value = target
        self.mock_repo.save.side_effect = lambda user: user

        result = self.use_case.execute(ForcePasswordResetCommand(user_id=2), admin)

        assert result.force_password_change is True
        self.mock_repo.save.assert_called_once_with(target)

    def test_force_reset_user_not_found(self):
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        self.mock_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError, match="User not found"):
            self.use_case.execute(ForcePasswordResetCommand(user_id=999), admin)

    def test_force_reset_rejects_insufficient_permissions(self):
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=1)
        target = User("Other Staff", "other@test.com", "hash", Role.STAFF, id=2)
        self.mock_repo.get_by_id.return_value = target

        with pytest.raises(ValidationError, match="Insufficient permissions to force password change"):
            self.use_case.execute(ForcePasswordResetCommand(user_id=2), staff)