# Tests for staff-specific user functionality.

import pytest
from features.users.domain.models.user import User, Role
from features.users.domain.services.user_service import UserDomainService


class TestStaffPermissions:
    """Staff permission tests."""

    def test_staff_can_manage_customers_only(self):
        """Test that staff can manage customers but not other staff/admins."""
        staff = User("Staff Member", "staff@test.com", "hash", Role.STAFF, id=1)
        customer = User("Customer", "cust@test.com", "hash", Role.CUSTOMER, id=2)
        other_staff = User("Other Staff", "staff2@test.com", "hash", Role.STAFF, id=3)

        assert UserDomainService.can_user_manage_others(staff, customer)
        assert not UserDomainService.can_user_manage_others(staff, other_staff)

    def test_staff_cannot_manage_self(self):
        """Staff users should not be able to manage themselves."""
        staff = User("Staff Member", "staff@test.com", "hash", Role.STAFF, id=1)
        assert not UserDomainService.can_user_manage_others(staff, staff)

    def test_staff_has_medium_role_hierarchy(self):
        """Test that staff has medium role hierarchy level."""
        assert UserDomainService.get_role_hierarchy_level(Role.STAFF) == 2

    def test_staff_can_be_promoted_to_admin(self):
        """Test that staff can be promoted to admin."""
        staff = User("Staff Member", "staff@test.com", "hash", Role.STAFF)

        assert UserDomainService.can_user_be_promoted(staff, Role.ADMIN)

    def test_staff_cannot_be_demoted_to_customer(self):
        """Test that staff cannot be demoted to customer."""
        staff = User("Staff Member", "staff@test.com", "hash", Role.STAFF)

        assert not UserDomainService.can_user_be_promoted(staff, Role.CUSTOMER)

    def test_staff_can_force_password_change_on_customer(self):
        """Test that staff can force password change on customers."""
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=1)
        customer = User("Customer", "cust@test.com", "hash", Role.CUSTOMER, id=2)

        assert UserDomainService.can_user_force_password_change(staff, customer)

    def test_staff_cannot_force_password_change_on_admin(self):
        """Test that staff cannot force password change on admins."""
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=1)
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=2)

        assert not UserDomainService.can_user_force_password_change(staff, admin)

    def test_staff_cannot_force_password_change_on_other_staff(self):
        """Test that staff cannot force password change on other staff."""
        staff1 = User("Staff 1", "staff1@test.com", "hash", Role.STAFF, id=1)
        staff2 = User("Staff 2", "staff2@test.com", "hash", Role.STAFF, id=2)

        assert not UserDomainService.can_user_force_password_change(staff1, staff2)
