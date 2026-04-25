from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from features.users.application.interfaces.admin_user_admin_repository_interface import (
    AdminUserAdminRepositoryInterface,
)
from features.users.application.use_cases.user_use_cases import (
    CreateStewardCommand,
    CreateStewardUseCase,
    ForcePasswordResetCommand,
    ForcePasswordResetUseCase,
    ListUsersQuery,
    ListUsersUseCase,
)
from features.users.domain.models.user import Role
from shared.domain.exceptions import ValidationError


@dataclass(frozen=True)
class StewardPayload:
    name: str
    email: str
    password: str
    phone: str | None = None


class SuspensionPolicyViolationError(ValidationError):
    """Raised when a suspension request violates business validation rules."""


class SuspensionPolicyConflictError(ValidationError):
    """Raised when a suspension request conflicts with system invariants."""


class UserAdminAccessDeniedError(ValidationError):
    """Raised when an admin action is not authorized by policy."""


class UserAdminConflictError(ValidationError):
    """Raised when an admin action conflicts with current state."""


class UserAdminNotFoundError(ValidationError):
    """Raised when an admin action targets a missing entity."""


class UserAdminActionsUseCase:
    def __init__(self, user_repo: AdminUserAdminRepositoryInterface):
        self.user_repo = user_repo
        self.list_users_use_case = ListUsersUseCase(self.user_repo)
        self.create_steward_use_case = CreateStewardUseCase(self.user_repo)
        self.force_password_reset_use_case = ForcePasswordResetUseCase(self.user_repo)

    def list_users(self, role_raw: str | None, search_text: str | None, requesting_user_id: int) -> list[dict[str, Any]]:
        role = None
        if role_raw:
            normalized = role_raw.strip().lower()
            if normalized not in {"customer", "staff", "admin"}:
                raise ValueError("Invalid role filter")
            role = Role(normalized)

        requesting_user = self.user_repo.get_by_id(requesting_user_id)
        if requesting_user is None:
            raise PermissionError("Authentication required")

        users = self.list_users_use_case.execute(
            ListUsersQuery(role=role, search_text=search_text),
            requesting_user,
        )
        return [self._serialize_user(user) for user in users]

    def create_steward(self, payload: StewardPayload, requesting_user_id: int, password_hash: str) -> dict[str, Any]:
        requesting_user = self.user_repo.get_by_id(requesting_user_id)
        if requesting_user is None:
            raise PermissionError("Authentication required")

        try:
            steward = self.create_steward_use_case.execute(
                CreateStewardCommand(
                    name=payload.name,
                    email=payload.email,
                    password_hash=password_hash,
                    phone=payload.phone,
                ),
                requesting_user,
            )
        except ValidationError as exc:
            message = str(exc)
            if message == "Admin access required":
                raise UserAdminAccessDeniedError(message) from exc
            if message == "email already exists":
                raise UserAdminConflictError(message) from exc
            raise
        return self._serialize_user(steward)

    def force_password_reset(self, user_id: int, requesting_user_id: int) -> dict[str, Any]:
        requesting_user = self.user_repo.get_by_id(requesting_user_id)
        if requesting_user is None:
            raise PermissionError("Authentication required")

        try:
            user = self.force_password_reset_use_case.execute(
                ForcePasswordResetCommand(user_id=user_id),
                requesting_user,
            )
        except ValidationError as exc:
            message = str(exc)
            if message == "User not found":
                raise UserAdminNotFoundError(message) from exc
            if message == "Insufficient permissions to force password change":
                raise UserAdminAccessDeniedError(message) from exc
            raise
        return self._serialize_user(user)

    def set_suspension(self, user_id: int, suspended: bool, acting_user_id: int) -> dict[str, Any]:
        target = self.user_repo.get_by_id(user_id)
        if target is None:
            raise LookupError("User not found")

        self._validate_suspension_policy(target=target, suspended=suspended, acting_user_id=acting_user_id)

        target.is_suspended = suspended
        saved = self.user_repo.save(target)
        return self._serialize_user(saved)

    def _validate_suspension_policy(self, *, target, suspended: bool, acting_user_id: int) -> None:
        if target.id == acting_user_id and suspended:
            raise SuspensionPolicyViolationError("You cannot suspend your own account.")

        if self._user_role_value(target) == "admin" and suspended:
            active_admin_count = len([
                user
                for user in self.user_repo.list_by_role("admin")
                if not bool(getattr(user, "is_suspended", False))
            ])
            if active_admin_count <= 1:
                raise SuspensionPolicyConflictError("Cannot suspend the last active admin account.")

    @staticmethod
    def _user_role_value(user) -> str | None:
        role = getattr(user, "role", None)
        if hasattr(role, "value"):
            role = role.value
        if isinstance(role, str):
            return role
        return None

    @staticmethod
    def _serialize_user(user) -> dict[str, Any]:
        role = getattr(user, "role", None)
        if hasattr(role, "value"):
            role = role.value
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "role": role,
            "force_password_change": bool(getattr(user, "force_password_change", False)),
            "is_suspended": bool(getattr(user, "is_suspended", False)),
        }
