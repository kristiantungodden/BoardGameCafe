from features.users.application.use_cases.auth_use_cases import LoginUseCase, RegisterUseCase
from features.users.application.use_cases.user_use_cases import UpdateOwnProfileUseCase
from features.users.infrastructure.adapters import (
    FlaskLoginSessionAdapter,
    WerkzeugPasswordHasher,
)
from features.users.infrastructure.repositories import SqlAlchemyUserRepository


def get_login_use_case() -> LoginUseCase:
    users = SqlAlchemyUserRepository()
    hasher = WerkzeugPasswordHasher()
    session = FlaskLoginSessionAdapter()
    return LoginUseCase(users, hasher, session)


def get_register_use_case() -> RegisterUseCase:
    users = SqlAlchemyUserRepository()
    hasher = WerkzeugPasswordHasher()
    return RegisterUseCase(users, hasher)


def get_update_profile_use_case() -> UpdateOwnProfileUseCase:
    users = SqlAlchemyUserRepository()
    return UpdateOwnProfileUseCase(users)