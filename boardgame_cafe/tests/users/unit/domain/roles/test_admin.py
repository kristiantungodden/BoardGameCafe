# Tests for admin-specific user functionality.

import pytest
from features.users.domain.models.user import User, Role
from features.users.domain.services.user_service import UserDomainService


class TestAdminPermissions:
    """Admin permission tests."""

    def test_admin_can_manage_any_user(self):
        """Test that admins can manage users of any role."""
        admin = User("Admin User", "admin@test.com", "hash", Role.ADMIN, id=1)
        customer = User("Customer", "cust@test.com", "hash", Role.CUSTOMER, id=2)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=3)

        assert UserDomainService.can_user_manage_others(admin, customer)
        assert UserDomainService.can_user_manage_others(admin, staff)

    def test_admin_cannot_manage_self(self):
        """Even admins should not be able to manage themselves."""
        admin = User("Admin User", "admin@test.com", "hash", Role.ADMIN, id=1)
        assert not UserDomainService.can_user_manage_others(admin, admin)

    def test_admin_has_highest_role_hierarchy(self):
        """Test that admin has the highest role hierarchy level."""
        assert UserDomainService.get_role_hierarchy_level(Role.ADMIN) == 3

    def test_admin_role_transition_fails(self):
        """Test that admins cannot change to any other role (already at top)."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN)

        assert not UserDomainService.can_user_be_promoted(admin, Role.CUSTOMER)
        assert not UserDomainService.can_user_be_promoted(admin, Role.STAFF)
        assert not UserDomainService.can_user_be_promoted(admin, Role.ADMIN)

    def test_admin_can_force_password_change_on_any_user(self):
        """Test that admins can force password change on any user."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        customer = User("Customer", "cust@test.com", "hash", Role.CUSTOMER, id=2)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=3)

        assert UserDomainService.can_user_force_password_change(admin, customer)
        assert UserDomainService.can_user_force_password_change(admin, staff)

    def test_admin_cannot_force_password_change_on_self(self):
        """Test that admins cannot force password change on themselves."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)

        assert not UserDomainService.can_user_force_password_change(admin, admin)