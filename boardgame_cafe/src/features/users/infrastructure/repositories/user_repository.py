from __future__ import annotations

from typing import Optional, Sequence

from features.users.application.interfaces import UserRepositoryInterface
from features.users.domain.models.user import Role, User
from features.users.infrastructure.database.user_db import UserDB
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
        row.is_suspended = user.is_suspended

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
        is_suspended=bool(getattr(row, "is_suspended", False)),
    )
