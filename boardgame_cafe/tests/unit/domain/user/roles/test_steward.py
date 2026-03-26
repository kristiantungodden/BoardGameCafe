# Tests for steward (staff) specific user functionality.

import pytest
from domain.models.user import User, Role
from domain.services.user_service import UserDomainService


class TestStewardPermissions:
    """Steward permission tests."""

    def test_steward_can_manage_customers_only(self):
        """Test that stewards can manage customers but not other staff/admins."""
        steward = User("Steward", "steward@test.com", "hash", Role.STAFF, id=1)
        customer = User("Customer", "cust@test.com", "hash", Role.CUSTOMER, id=2)
        other_steward = User("Other Steward", "steward2@test.com", "hash", Role.STAFF, id=3)

        assert UserDomainService.can_user_manage_others(steward, customer)
        assert not UserDomainService.can_user_manage_others(steward, other_steward)

    def test_steward_has_medium_role_hierarchy(self):
        """Test that steward has medium role hierarchy level."""
        assert UserDomainService.get_role_hierarchy_level(Role.STAFF) == 2

    def test_steward_can_be_promoted_to_admin(self):
        """Test that stewards can be promoted to admin."""
        steward = User("Steward", "steward@test.com", "hash", Role.STAFF)

        assert UserDomainService.can_user_be_promoted(steward, Role.ADMIN)

    def test_steward_cannot_be_demoted_to_customer(self):
        """Test that stewards cannot be demoted to customer."""
        steward = User("Steward", "steward@test.com", "hash", Role.STAFF)

        assert not UserDomainService.can_user_be_promoted(steward, Role.CUSTOMER)