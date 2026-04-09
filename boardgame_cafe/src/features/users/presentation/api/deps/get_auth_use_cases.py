from __future__ import annotations

from typing import Optional

from flask_login import current_user, login_user, logout_user

from features.users.application.interfaces import (
    AuthSessionPortInterface,
    PasswordHasherInterface,
)
from features.users.application.use_cases.auth_use_cases import LoginUseCase, RegisterUseCase
from features.users.application.use_cases.user_use_cases import (
    CreateUserUseCase,
    UpdateUserUseCase,
    ChangePasswordUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    DeleteUserUseCase,
)
from features.users.domain.models.user import Role, User
from features.users.infrastructure import UserDB, hash_password, verify_password
from features.users.infrastructure.repositories import SqlAlchemyUserRepository
from shared.infrastructure import db


class WerkZeugPasswordHasher(PasswordHasherInterface):
    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, hashed: str, password: str) -> bool:
        return verify_password(hashed, password)


class FlaskLoginSessionPort(AuthSessionPortInterface):
    def login(self, user_id: int) -> None:
        row = db.session.get(UserDB, user_id)
        if row is None:
            return
        login_user(row)

    def logout(self) -> None:
        logout_user()

    def get_current_user_id(self) -> Optional[int]:
        if getattr(current_user, "is_authenticated", False):
            return int(current_user.get_id())
        return None


def get_login_use_case() -> LoginUseCase:
    users = SqlAlchemyUserRepository()
    hasher = WerkZeugPasswordHasher()
    session = FlaskLoginSessionPort()
    return LoginUseCase(users, hasher, session)

def get_register_use_case() -> RegisterUseCase:
    users = SqlAlchemyUserRepository()
    hasher = WerkZeugPasswordHasher()
    return RegisterUseCase(users, hasher)


# User management use cases (steward/admin routes)
def get_create_user_use_case() -> CreateUserUseCase:
    users = SqlAlchemyUserRepository()
    return CreateUserUseCase(users)


def get_update_user_use_case() -> UpdateUserUseCase:
    users = SqlAlchemyUserRepository()
    return UpdateUserUseCase(users)


def get_change_password_use_case() -> ChangePasswordUseCase:
    users = SqlAlchemyUserRepository()
    return ChangePasswordUseCase(users)


def get_get_user_use_case() -> GetUserUseCase:
    users = SqlAlchemyUserRepository()
    return GetUserUseCase(users)


def get_list_users_use_case() -> ListUsersUseCase:
    users = SqlAlchemyUserRepository()
    return ListUsersUseCase(users)


def get_delete_user_use_case() -> DeleteUserUseCase:
    users = SqlAlchemyUserRepository()
    return DeleteUserUseCase(users)