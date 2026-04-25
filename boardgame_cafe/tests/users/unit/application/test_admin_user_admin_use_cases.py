import pytest

from features.users.application.use_cases.admin_user_admin_use_cases import (
    SuspensionPolicyConflictError,
    SuspensionPolicyViolationError,
    UserAdminActionsUseCase,
)
from features.users.domain.models.user import Role, User


class FakeAdminRepo:
    def __init__(self, users):
        self._users = {int(user.id): user for user in users}

    def get_by_id(self, user_id: int):
        return self._users.get(int(user_id))

    def list_by_role(self, role: str):
        return [u for u in self._users.values() if getattr(getattr(u, "role", None), "value", None) == role]

    def save(self, user: User):
        self._users[int(user.id)] = user
        return user


def test_set_suspension_rejects_self_suspension():
    admin = User("Admin", "admin@example.com", "hash", Role.ADMIN, id=1)
    repo = FakeAdminRepo([admin])
    use_case = UserAdminActionsUseCase(repo)

    with pytest.raises(SuspensionPolicyViolationError, match="You cannot suspend your own account"):
        use_case.set_suspension(user_id=1, suspended=True, acting_user_id=1)


def test_set_suspension_rejects_last_active_admin():
    active_admin = User("Only Admin", "only-admin@example.com", "hash", Role.ADMIN, id=1)
    target_admin = User("Target Admin", "target-admin@example.com", "hash", Role.ADMIN, id=2)
    target_admin.is_suspended = True

    repo = FakeAdminRepo([active_admin, target_admin])
    use_case = UserAdminActionsUseCase(repo)

    with pytest.raises(SuspensionPolicyConflictError, match="Cannot suspend the last active admin account"):
        use_case.set_suspension(user_id=1, suspended=True, acting_user_id=999)


def test_set_suspension_updates_user_when_policy_allows():
    acting_admin = User("Acting", "acting@example.com", "hash", Role.ADMIN, id=1)
    target_user = User("Customer", "customer@example.com", "hash", Role.CUSTOMER, id=2)

    repo = FakeAdminRepo([acting_admin, target_user])
    use_case = UserAdminActionsUseCase(repo)

    result = use_case.set_suspension(user_id=2, suspended=True, acting_user_id=1)

    assert result["id"] == 2
    assert result["is_suspended"] is True
