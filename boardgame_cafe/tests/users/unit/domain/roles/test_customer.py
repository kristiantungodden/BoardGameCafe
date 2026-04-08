# Tests for customer-specific user functionality.

import pytest
from features.users.domain.models.user import User, Role
from features.users.domain.services.user_service import UserDomainService
from shared.domain.exceptions import ValidationError


class TestCustomerCoreFunctionality:
    """Core customer functionality tests."""

    def test_customer_creation(self):
        """Test basic customer user creation."""
        customer = User("John Doe", "john@test.com", "hash123", Role.CUSTOMER)
        assert customer.name == "John Doe"
        assert customer.email == "john@test.com"
        assert customer.is_customer()
        assert not customer.can_access_admin_features()

    def test_customer_password_management(self):
        """Test customer password operations."""
        customer = User("Jane Doe", "jane@test.com", "old_hash", Role.CUSTOMER)

        # Change password
        customer.change_password("new_hash")
        assert customer.password_hash == "new_hash"
        assert not customer.force_password_change

        # Force password reset
        customer.force_password_reset()
        assert customer.force_password_change

    def test_customer_profile_updates(self):
        """Test customer profile management."""
        customer = User("Bob", "bob@test.com", "hash", Role.CUSTOMER)

        # Update name
        customer.update_profile(name="Bob Updated")
        assert customer.name == "Bob Updated"

        # Update phone
        customer.update_profile(phone="12345678")
        assert customer.phone == "12345678"

        # Update both
        customer.update_profile(name="Bob Final", phone="87654321")
        assert customer.name == "Bob Final"
        assert customer.phone == "87654321"


class TestCustomerPermissions:
    """Customer permission and role tests."""

    def test_customer_role_restrictions(self):
        """Test customer role limitations."""
        customer = User("Customer", "cust@test.com", "hash", Role.CUSTOMER)

        # Cannot manage others
        other_customer = User("Other", "other@test.com", "hash", Role.CUSTOMER)
        assert not UserDomainService.can_user_manage_others(customer, other_customer)
        assert not UserDomainService.can_user_manage_others(customer, customer)

        # Cannot access admin features
        assert not customer.can_access_admin_features()

        # Has lowest role hierarchy
        assert UserDomainService.get_role_hierarchy_level(Role.CUSTOMER) == 1

    def test_customer_promotion_eligibility(self):
        """Test customer can be promoted to staff/admin."""
        customer = User("Customer", "cust@test.com", "hash", Role.CUSTOMER)

        # Can be promoted to staff
        assert UserDomainService.can_user_be_promoted(customer, Role.STAFF)

        # Can be promoted to admin
        assert UserDomainService.can_user_be_promoted(customer, Role.ADMIN)

        # Cannot be promoted to same role
        assert not UserDomainService.can_user_be_promoted(customer, Role.CUSTOMER)