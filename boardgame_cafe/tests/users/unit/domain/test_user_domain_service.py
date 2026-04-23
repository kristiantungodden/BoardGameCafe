"""
Unit tests for UserDomainService.

These tests ensure the UserDomainService properly implements business rules
for user management, role hierarchies, and permissions.
"""
import pytest

from features.users.domain.models.user import User, Role
from features.users.domain.services.user_service import UserDomainService
from shared.domain.exceptions import ValidationError


class TestRoleHierarchy:
    """Test suite for role hierarchy business rules."""
    
    def test_get_role_hierarchy_level_returns_correct_levels(self):
        """RULE: Role hierarchy levels should be: Customer=1, Staff=2, Admin=3."""
        assert UserDomainService.get_role_hierarchy_level(Role.CUSTOMER) == 1
        assert UserDomainService.get_role_hierarchy_level(Role.STAFF) == 2
        assert UserDomainService.get_role_hierarchy_level(Role.ADMIN) == 3
    
    def test_is_higher_role_compares_roles_correctly(self):
        """RULE: Admin > Staff > Customer in hierarchy."""
        # Admin is higher than Staff and Customer
        assert UserDomainService.is_higher_role(Role.ADMIN, Role.STAFF) is True
        assert UserDomainService.is_higher_role(Role.ADMIN, Role.CUSTOMER) is True
        
        # Staff is higher than Customer
        assert UserDomainService.is_higher_role(Role.STAFF, Role.CUSTOMER) is True
        
        # Customer is not higher than anyone
        assert UserDomainService.is_higher_role(Role.CUSTOMER, Role.STAFF) is False
        assert UserDomainService.is_higher_role(Role.CUSTOMER, Role.ADMIN) is False
        
        # Same role is not higher
        assert UserDomainService.is_higher_role(Role.ADMIN, Role.ADMIN) is False
        assert UserDomainService.is_higher_role(Role.STAFF, Role.STAFF) is False
        assert UserDomainService.is_higher_role(Role.CUSTOMER, Role.CUSTOMER) is False


class TestUserManagementPermissions:
    """Test suite for user management permission business rules."""
    
    def test_admin_can_manage_anyone(self):
        """RULE: Admins can manage anyone (except themselves)."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)
        customer = User("Customer", "customer@test.com", "hash", Role.CUSTOMER, id=3)
        
        assert UserDomainService.can_user_manage_others(admin, staff) is True
        assert UserDomainService.can_user_manage_others(admin, customer) is True
        assert UserDomainService.can_user_manage_others(admin, admin) is False  # Cannot manage self
    
    def test_staff_can_manage_customers_only(self):
        """RULE: Staff can manage customers only."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)
        customer = User("Customer", "customer@test.com", "hash", Role.CUSTOMER, id=3)
        
        assert UserDomainService.can_user_manage_others(staff, customer) is True
        assert UserDomainService.can_user_manage_others(staff, staff) is False
        assert UserDomainService.can_user_manage_others(staff, admin) is False
        assert UserDomainService.can_user_manage_others(staff, staff) is False  # Cannot manage self
    
    def test_customer_cannot_manage_anyone(self):
        """RULE: Customers cannot manage anyone."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)
        customer = User("Customer", "customer@test.com", "hash", Role.CUSTOMER, id=3)
        
        assert UserDomainService.can_user_manage_others(customer, admin) is False
        assert UserDomainService.can_user_manage_others(customer, staff) is False
        assert UserDomainService.can_user_manage_others(customer, customer) is False  # Cannot manage self


class TestForcePasswordChangePermissions:
    """Test suite for force password change permission business rules."""
    
    def test_can_user_force_password_change_follows_management_rules(self):
        """RULE: Only users who can manage others can force password change."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)
        customer = User("Customer", "customer@test.com", "hash", Role.CUSTOMER, id=3)
        
        # Admin can force password change on staff and customers
        assert UserDomainService.can_user_force_password_change(admin, staff) is True
        assert UserDomainService.can_user_force_password_change(admin, customer) is True
        
        # Staff can force password change on customers only
        assert UserDomainService.can_user_force_password_change(staff, customer) is True
        assert UserDomainService.can_user_force_password_change(staff, admin) is False
        
        # Customer cannot force password change on anyone
        assert UserDomainService.can_user_force_password_change(customer, admin) is False
        assert UserDomainService.can_user_force_password_change(customer, staff) is False


class TestUserPromotion:
    """Test suite for user promotion business rules."""
    
    def test_can_user_be_promoted_allows_valid_promotions(self):
        """RULE: Users can be promoted to higher roles."""
        customer = User("Customer", "customer@test.com", "hash", Role.CUSTOMER, id=1)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=3)
        
        # Customer can be promoted to Staff or Admin
        assert UserDomainService.can_user_be_promoted(customer, Role.STAFF) is True
        assert UserDomainService.can_user_be_promoted(customer, Role.ADMIN) is True
        
        # Staff can be promoted to Admin
        assert UserDomainService.can_user_be_promoted(staff, Role.ADMIN) is True
    
    def test_can_user_be_promoted_rejects_invalid_promotions(self):
        """RULE: Users cannot be demoted or stay in same role."""
        customer = User("Customer", "customer@test.com", "hash", Role.CUSTOMER, id=1)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=3)
        
        # Admin cannot be promoted (already highest)
        assert UserDomainService.can_user_be_promoted(admin, Role.STAFF) is False
        assert UserDomainService.can_user_be_promoted(admin, Role.CUSTOMER) is False
        assert UserDomainService.can_user_be_promoted(admin, Role.ADMIN) is False
        
        # Staff cannot be demoted to Customer
        assert UserDomainService.can_user_be_promoted(staff, Role.CUSTOMER) is False
        assert UserDomainService.can_user_be_promoted(staff, Role.STAFF) is False
        
        # Customer cannot stay as Customer
        assert UserDomainService.can_user_be_promoted(customer, Role.CUSTOMER) is False


class TestRoleTransitionValidation:
    """Test suite for role transition validation business rules."""
    
    def test_validate_role_transition_allows_valid_transitions(self):
        """RULE: Valid role transitions should not raise exceptions."""
        # These should not raise any exception
        UserDomainService.validate_role_transition(Role.CUSTOMER, Role.STAFF)
        UserDomainService.validate_role_transition(Role.CUSTOMER, Role.ADMIN)
        UserDomainService.validate_role_transition(Role.STAFF, Role.ADMIN)
    
    def test_validate_role_transition_rejects_invalid_transitions(self):
        """RULE: Invalid role transitions should raise ValidationError."""
        # Admin cannot transition to lower roles
        with pytest.raises(ValidationError):
            UserDomainService.validate_role_transition(Role.ADMIN, Role.STAFF)
        
        with pytest.raises(ValidationError):
            UserDomainService.validate_role_transition(Role.ADMIN, Role.CUSTOMER)
        
        # Staff cannot transition to Customer
        with pytest.raises(ValidationError):
            UserDomainService.validate_role_transition(Role.STAFF, Role.CUSTOMER)
        
        # Same role transition is invalid
        with pytest.raises(ValidationError):
            UserDomainService.validate_role_transition(Role.CUSTOMER, Role.CUSTOMER)
        
        with pytest.raises(ValidationError):
            UserDomainService.validate_role_transition(Role.STAFF, Role.STAFF)
        
        with pytest.raises(ValidationError):
            UserDomainService.validate_role_transition(Role.ADMIN, Role.ADMIN)


class TestRequiresPasswordChange:
    """Test suite for password change requirement business rules."""
    
    def test_requires_password_change_returns_correct_status(self):
        """RULE: requires_password_change should return the force_password_change flag."""
        user_with_flag = User("User", "user@test.com", "hash", force_password_change=True)
        user_without_flag = User("User", "user@test.com", "hash", force_password_change=False)
        
        assert UserDomainService.requires_password_change(user_with_flag) is True
        assert UserDomainService.requires_password_change(user_without_flag) is False


class TestEdgeCases:
    """Test suite for edge cases in user domain service."""
    
    def test_cannot_manage_self_regardless_of_role(self):
        """RULE: Users cannot manage themselves regardless of their role."""
        admin = User("Admin", "admin@test.com", "hash", Role.ADMIN, id=1)
        staff = User("Staff", "staff@test.com", "hash", Role.STAFF, id=2)
        customer = User("Customer", "customer@test.com", "hash", Role.CUSTOMER, id=3)
        
        assert UserDomainService.can_user_manage_others(admin, admin) is False
        assert UserDomainService.can_user_manage_others(staff, staff) is False
        assert UserDomainService.can_user_manage_others(customer, customer) is False
    
    def test_management_based_on_role_not_id(self):
        """RULE: Management permissions are based on role, not user ID."""
        # Create two users with same role but different IDs
        admin1 = User("Admin1", "admin1@test.com", "hash", Role.ADMIN, id=1)
        admin2 = User("Admin2", "admin2@test.com", "hash", Role.ADMIN, id=2)
        
        # Admin1 can manage admin2 (different users, admin can manage anyone)
        assert UserDomainService.can_user_manage_others(admin1, admin2) is True
        
        # But admin1 cannot manage themselves
        assert UserDomainService.can_user_manage_others(admin1, admin1) is False