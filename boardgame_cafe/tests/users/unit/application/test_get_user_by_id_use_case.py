from unittest.mock import Mock

from features.users.application.use_cases.user_use_cases import (
    GetUserByIdQuery,
    GetUserByIdUseCase,
)
from features.users.domain.models.user import Role, User


def test_get_user_by_id_use_case_returns_user_from_repository():
    repo = Mock()
    expected_user = User(
        id=12,
        name="Alice",
        email="alice@example.com",
        password_hash="hashed",
        role=Role.CUSTOMER,
    )
    repo.get_by_id.return_value = expected_user

    use_case = GetUserByIdUseCase(repo)

    result = use_case.execute(GetUserByIdQuery(user_id=12))

    assert result is expected_user
    repo.get_by_id.assert_called_once_with(12)


def test_get_user_by_id_use_case_returns_none_when_missing():
    repo = Mock()
    repo.get_by_id.return_value = None

    use_case = GetUserByIdUseCase(repo)

    result = use_case.execute(GetUserByIdQuery(user_id=404))

    assert result is None
    repo.get_by_id.assert_called_once_with(404)
