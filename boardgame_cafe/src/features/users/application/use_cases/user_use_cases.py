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
class UpdateOwnProfileCommand:
    user_id: int
    name: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class ChangePasswordCommand:
    user_id: int
    new_password_hash: str


@dataclass
class CreateStewardCommand:
    name: str
    email: str
    password_hash: str
    phone: Optional[str] = None


@dataclass
class ListUsersQuery:
    role: Optional[Role] = None
    search_text: Optional[str] = None


@dataclass
class ForcePasswordResetCommand:
    user_id: int


class CreateUserUseCase:
    """Use case for creating new users."""

    def __init__(self, user_repo):
        self.user_repo = user_repo

    def execute(self, cmd: CreateUserCommand) -> User:
        """Create a new user with validation."""
        user = User(
            name=cmd.name,
            email=cmd.email,
            password_hash=cmd.password_hash,
            role=cmd.role,
            phone=cmd.phone,
        )
        return self.user_repo.save(user)


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

        original_role = target_user.role

        try:
            # Validate role change if requested
            if cmd.role is not None and cmd.role != target_user.role:
                UserDomainService.validate_role_transition(target_user.role, cmd.role)
                target_user.role = cmd.role

            # Update profile information
            target_user.update_profile(name=cmd.name, phone=cmd.phone)
        except ValidationError:
            target_user.role = original_role
            raise

        return self.user_repo.save(target_user)


class UpdateOwnProfileUseCase:
    """Use case for updating the signed-in user's profile."""

    def __init__(self, user_repo):
        self.user_repo = user_repo

    def execute(self, cmd: UpdateOwnProfileCommand, requesting_user: User) -> User:
        """Update the current user's profile details."""
        target_user = self.user_repo.get_by_id(cmd.user_id)
        if not target_user:
            raise ValidationError("User not found")

        if requesting_user.id != target_user.id:
            raise ValidationError("Users can only update their own profile")

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


@dataclass
class GetUserByIdQuery:
    user_id: int


class GetUserByIdUseCase:
    """Use case for retrieving a single user by id."""

    def __init__(self, user_repo):
        self.user_repo = user_repo

    def execute(self, query: GetUserByIdQuery) -> User | None:
        return self.user_repo.get_by_id(query.user_id)


class CreateStewardUseCase:
    """Use case for admin-driven steward provisioning."""

    def __init__(self, user_repo):
        self.user_repo = user_repo

    def execute(self, cmd: CreateStewardCommand, requesting_user: User) -> User:
        """Create a steward account that must change password on first login."""
        if requesting_user.role != Role.ADMIN:
            raise ValidationError("Admin access required")

        if self.user_repo.get_by_email(cmd.email):
            raise ValidationError("email already exists")

        user = User(
            name=cmd.name,
            email=cmd.email,
            password_hash=cmd.password_hash,
            role=Role.STAFF,
            phone=cmd.phone,
        )
        user.force_password_reset()
        return self.user_repo.save(user)


class ListUsersUseCase:
    """Use case for user listing and filtering."""

    def __init__(self, user_repo):
        self.user_repo = user_repo

    def execute(self, query: ListUsersQuery, requesting_user: User) -> list[User]:
        if requesting_user.role not in (Role.ADMIN, Role.STAFF):
            raise ValidationError("Insufficient permissions to list users")

        if query.role is not None:
            users = list(self.user_repo.list_by_role(query.role.value))
        else:
            users = list(self.user_repo.list_all())

        search_text = (query.search_text or "").strip().lower()
        if not search_text:
            return users

        return [
            user for user in users
            if search_text in user.name.lower() or search_text in user.email.lower()
        ]


class ForcePasswordResetUseCase:
    """Use case for forcing password change on another user."""

    def __init__(self, user_repo):
        self.user_repo = user_repo

    def execute(self, cmd: ForcePasswordResetCommand, requesting_user: User) -> User:
        target_user = self.user_repo.get_by_id(cmd.user_id)
        if not target_user:
            raise ValidationError("User not found")

        if not UserDomainService.can_user_force_password_change(requesting_user, target_user):
            raise ValidationError("Insufficient permissions to force password change")

        target_user.force_password_reset()
        return self.user_repo.save(target_user)