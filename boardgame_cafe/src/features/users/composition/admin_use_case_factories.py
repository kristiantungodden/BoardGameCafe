from features.users.application.use_cases.user_use_cases import (
    CreateStewardUseCase,
    ForcePasswordResetUseCase,
    ListUsersUseCase,
)
from features.users.infrastructure.repositories import SqlAlchemyUserRepository


def get_create_steward_use_case() -> CreateStewardUseCase:
    return CreateStewardUseCase(SqlAlchemyUserRepository())


def get_list_users_use_case() -> ListUsersUseCase:
    return ListUsersUseCase(SqlAlchemyUserRepository())


def get_force_password_reset_use_case() -> ForcePasswordResetUseCase:
    return ForcePasswordResetUseCase(SqlAlchemyUserRepository())
