"""Domain services for user management.

Domain services contain business logic that doesn't naturally belong
to a single entity but involves multiple entities or complex business rules.
"""

from typing import Optional
from domain.models.user import User, Role
from domain.exceptions import ValidationError


class UserDomainService:
    """Domain service for user-related business operations."""

    @staticmethod
    def get_role_hierarchy_level(role: Role) -> int:
        """Get the hierarchy level of a role (higher number = more permissions)."""
        hierarchy = {
            Role.CUSTOMER: 1,
            Role.STAFF: 2,
            Role.ADMIN: 3
        }
        return hierarchy[role]

    @staticmethod
    def is_higher_role(role1: Role, role2: Role) -> bool:
        """Check if role1 has higher hierarchy than role2."""
        return UserDomainService.get_role_hierarchy_level(role1) > UserDomainService.get_role_hierarchy_level(role2)

    @staticmethod
    def can_user_manage_others(user: User, target_user: User) -> bool:
        """Check if a user can manage another user.

        Business rules:
        - Admins can manage anyone
        - Staff can manage customers only
        - Customers cannot manage anyone
        - Users cannot manage themselves
        """
        if user.id == target_user.id:
            return False  # Cannot manage self

        if user.role == Role.ADMIN:
            return True

        if user.role == Role.STAFF and target_user.role == Role.CUSTOMER:
            return True

        return False

    @staticmethod
    def can_user_force_password_change(user: User, target_user: User) -> bool:
        """Check if a user can force password change on another user."""
        return UserDomainService.can_user_manage_others(user, target_user)

    @staticmethod
    def can_user_be_promoted(user: User, new_role: Role) -> bool:
        """Check if a user can be promoted to a new role."""
        if user.role == new_role:
            return False

        if user.role == Role.ADMIN:
            return False

        if user.role == Role.STAFF and new_role == Role.CUSTOMER:
            return False

        return True

    @staticmethod
    def validate_role_transition(current_role: Role, new_role: Role) -> None:
        """Validate role transition business rules."""
        if not UserDomainService.can_user_be_promoted(
            User("temp", "temp@test.com", "hash", current_role), new_role
        ):
            raise ValidationError(
                f"Invalid role transition from {current_role.value} to {new_role.value}"
            )

    @staticmethod
    def requires_password_change(user: User) -> bool:
        """Check if user needs to change password."""
        return user.force_password_change