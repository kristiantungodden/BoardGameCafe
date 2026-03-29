"""Unit-style presentation tests for /api/auth/login.

These tests should isolate the route by monkeypatching `get_login_use_case`.
Tests use proper fake implementations of dependency interfaces.
"""

from typing import Optional

import pytest

from features.users.application.interfaces import (
    UserRepositoryInterface,
    PasswordHasherInterface,
    AuthSessionPortInterface,
)
from features.users.application.use_cases.auth_use_cases import LoginCommand, LoginUseCase
from features.users.domain.models.user import User, Role
from features.users.presentation.api import auth_routes
from shared.domain.exceptions import ValidationError


# Fake Implementations of Dependency Interfaces


class FakeUserRepository(UserRepositoryInterface):
    """Fake repository for testing."""

    def __init__(self, user: Optional[User] = None):
        self.user = user
        self.saved_users = []

    def get_by_id(self, user_id: int) -> Optional[User]:
        if self.user and self.user.id == user_id:
            return self.user
        return None

    def get_by_email(self, email: str) -> Optional[User]:
        if self.user and self.user.email == email:
            return self.user
        return None

    def save(self, user: User) -> User:
        self.saved_users.append(user)
        return user

    def delete(self, user_id: int) -> bool:
        return True

    def list_all(self):
        if self.user:
            return [self.user]
        return []

    def list_by_role(self, role: str):
        if self.user and self.user.role.value == role:
            return [self.user]
        return []


class FakePasswordHasher(PasswordHasherInterface):
    """Fake password hasher for testing."""

    def hash(self, password: str) -> str:
        return f"hashed_{password}"

    def verify(self, hashed: str, password: str) -> bool:
        return hashed == f"hashed_{password}"


class FakeAuthSessionPort(AuthSessionPortInterface):
    """Fake auth session port for testing."""

    def __init__(self):
        self.logged_in_user_id = None

    def login(self, user_id: int) -> None:
        self.logged_in_user_id = user_id

    def logout(self) -> None:
        self.logged_in_user_id = None

    def get_current_user_id(self) -> Optional[int]:
        return self.logged_in_user_id


# Tests


def test_login_returns_200_with_user_payload_on_valid_credentials(client, monkeypatch):
    """Test successful login returns 200 with user info."""
    test_user = User(
        id=1,
        name="John Doe",
        email="john@example.com",
        password_hash="hashed_SecurePass123",
        role=Role.CUSTOMER,
        phone="12345678",
        force_password_change=False,
    )

    fake_repo = FakeUserRepository(user=test_user)
    fake_hasher = FakePasswordHasher()
    fake_session = FakeAuthSessionPort()

    def get_fake_use_case():
        return LoginUseCase(fake_repo, fake_hasher, fake_session)

    monkeypatch.setattr(auth_routes, "get_login_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/login",
        json={
            "email": "john@example.com",
            "password": "SecurePass123",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Logged in"
    assert data["user"]["email"] == "john@example.com"
    assert data["user"]["name"] == "John Doe"
    assert data["user"]["id"] == 1
    assert fake_session.logged_in_user_id == 1


def test_login_returns_400_for_invalid_json(client, monkeypatch):
    """Test login route returns 400 for invalid JSON."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()
    fake_session = FakeAuthSessionPort()

    def get_fake_use_case():
        return LoginUseCase(fake_repo, fake_hasher, fake_session)

    monkeypatch.setattr(auth_routes, "get_login_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/login",
        data="invalid json {",
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Invalid JSON body"


def test_login_returns_400_for_schema_validation_error(client, monkeypatch):
    """Test login route returns 400 for missing required fields."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()
    fake_session = FakeAuthSessionPort()

    def get_fake_use_case():
        return LoginUseCase(fake_repo, fake_hasher, fake_session)

    monkeypatch.setattr(auth_routes, "get_login_use_case", get_fake_use_case)

    # Missing password field
    response = client.post(
        "/api/auth/login",
        json={
            "email": "john@example.com",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Validation failed"
    assert "details" in data


def test_login_returns_401_on_invalid_credentials(client, monkeypatch):
    """Test login route returns 401 for invalid credentials."""
    test_user = User(
        id=1,
        name="John Doe",
        email="john@example.com",
        password_hash="hashed_CorrectPassword123",
        role=Role.CUSTOMER,
    )

    fake_repo = FakeUserRepository(user=test_user)
    fake_hasher = FakePasswordHasher()
    fake_session = FakeAuthSessionPort()

    def get_fake_use_case():
        return LoginUseCase(fake_repo, fake_hasher, fake_session)

    monkeypatch.setattr(auth_routes, "get_login_use_case", get_fake_use_case)

    # Send wrong password
    response = client.post(
        "/api/auth/login",
        json={
            "email": "john@example.com",
            "password": "WrongPassword123",
        },
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Invalid credentials"
    # Verify user was not logged in
    assert fake_session.logged_in_user_id is None


def test_login_returns_401_for_nonexistent_user(client, monkeypatch):
    """Test login route returns 401 when user doesn't exist."""
    fake_repo = FakeUserRepository(user=None)
    fake_hasher = FakePasswordHasher()
    fake_session = FakeAuthSessionPort()

    def get_fake_use_case():
        return LoginUseCase(fake_repo, fake_hasher, fake_session)

    monkeypatch.setattr(auth_routes, "get_login_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123",
        },
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["error"] == "Invalid credentials"
