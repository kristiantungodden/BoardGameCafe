"""Use cases for user management."""

from dataclasses import dataclass
from typing import Optional

from features.users.domain.models.user import User, Role
from features.users.domain.services.user_service import UserDomainService
from shared.domain.exceptions import ValidationError


@dataclass
class CreateUserCommand:
    name: str
    email: str
    password_hash: str  # Pre-hashed from infrastructure
    role: Role = Role.CUSTOMER
    phone: Optional[str] = None


@dataclass
class UpdateUserCommand:
    user_id: int
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[Role] = None


@dataclass
class ChangePasswordCommand:
    user_id: int
    new_password_hash: str


class CreateUserUseCase:
    """Use case for creating new users."""

    def execute(self, cmd: CreateUserCommand) -> User:
        """Create a new user with validation."""
        user = User(
            name=cmd.name,
            email=cmd.email,
            password_hash=cmd.password_hash,
            role=cmd.role,
            phone=cmd.phone,
        )
        return user


class UpdateUserUseCase:
    """Use case for updating user information."""

    def __init__(self, user_repo):
        self.user_repo = user_repo

    def execute(self, cmd: UpdateUserCommand, requesting_user: User) -> User:
        """Update user with authorization checks."""
        target_user = self.user_repo.get_by_id(cmd.user_id)
        if not target_user:
            raise ValidationError("User not found")

        # Check permissions
        if not UserDomainService.can_user_manage_others(requesting_user, target_user):
            raise ValidationError("Insufficient permissions to update user")

        # Validate role change if requested
        if cmd.role is not None and cmd.role != target_user.role:
            UserDomainService.validate_role_transition(target_user.role, cmd.role)
            target_user.role = cmd.role

        # Update profile information
        target_user.update_profile(name=cmd.name, phone=cmd.phone)

        return self.user_repo.save(target_user)


class ChangePasswordUseCase:
    """Use case for changing user passwords."""

    def __init__(self, user_repo):
        self.user_repo = user_repo

    def execute(self, cmd: ChangePasswordCommand, requesting_user: User) -> User:
        """Change user password with authorization."""
        target_user = self.user_repo.get_by_id(cmd.user_id)
        if not target_user:
            raise ValidationError("User not found")

        # Users can change their own password, or admins can change anyone's
        if (requesting_user.id != target_user.id and
            not UserDomainService.can_user_manage_others(requesting_user, target_user)):
            raise ValidationError("Insufficient permissions to change password")

        target_user.change_password(cmd.new_password_hash)
        return self.user_repo.save(target_user)