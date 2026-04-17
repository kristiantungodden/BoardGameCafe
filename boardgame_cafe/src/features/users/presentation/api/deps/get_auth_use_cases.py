from __future__ import annotations

from typing import Optional, Sequence

from flask_login import current_user, login_user, logout_user

from features.users.application.interfaces import (
    AuthSessionPortInterface,
    PasswordHasherInterface,
    UserRepositoryInterface,
)
from features.users.application.use_cases.auth_use_cases import LoginUseCase, RegisterUseCase
from features.users.application.use_cases.user_use_cases import UpdateOwnProfileUseCase
from features.users.domain.models.user import Role, User
from features.users.infrastructure import UserDB, hash_password, verify_password
from shared.infrastructure import db


class SqlAlchemyUserRepository(UserRepositoryInterface):
    def get_by_id(self, user_id: int) -> Optional[User]:
        row = db.session.get(UserDB, user_id)
        return _to_domain(row)

    def get_by_email(self, email: str) -> Optional[User]:
        row = UserDB.query.filter_by(email=email).first()
        return _to_domain(row)

    def save(self, user: User) -> User:
        row = db.session.get(UserDB, user.id) if user.id else None
        if row is None:
            row = UserDB()
            db.session.add(row)

        row.name = user.name
        row.email = user.email
        row.phone = user.phone
        row.role = user.role.value
        row.password_hash = user.password_hash
        row.force_password_change = user.force_password_change

        db.session.commit()
        return _to_domain(row)

    def delete(self, user_id: int) -> bool:
        row = db.session.get(UserDB, user_id)
        if row is None:
            return False
        db.session.delete(row)
        db.session.commit()
        return True

    def list_all(self) -> Sequence[User]:
        return [_to_domain(row) for row in UserDB.query.all()]

    def list_by_role(self, role: str) -> Sequence[User]:
        return [_to_domain(row) for row in UserDB.query.filter_by(role=role).all()]


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


def _to_domain(row: Optional[UserDB]) -> Optional[User]:
    if row is None:
        return None
    return User(
        id=row.id,
        name=row.name,
        email=row.email,
        phone=row.phone,
        role=Role(row.role),
        password_hash=row.password_hash,
        force_password_change=row.force_password_change,
    )


def get_login_use_case() -> LoginUseCase:
    users = SqlAlchemyUserRepository()
    hasher = WerkZeugPasswordHasher()
    session = FlaskLoginSessionPort()
    return LoginUseCase(users, hasher, session)

def get_register_use_case() -> RegisterUseCase:
    users = SqlAlchemyUserRepository()
    hasher = WerkZeugPasswordHasher()
    return RegisterUseCase(users, hasher)


def get_update_profile_use_case() -> UpdateOwnProfileUseCase:
    users = SqlAlchemyUserRepository()
    return UpdateOwnProfileUseCase(users)