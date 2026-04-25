from __future__ import annotations

from typing import Protocol, Sequence

from features.users.domain.models.user import User


class AdminUserAdminRepositoryInterface(Protocol):
    def get_by_id(self, user_id: int) -> User | None:
        ...

    def list_by_role(self, role: str) -> Sequence[User]:
        ...

    def save(self, user: User) -> User:
        ...
