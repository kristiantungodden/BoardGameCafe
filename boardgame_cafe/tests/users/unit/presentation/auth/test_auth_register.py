"""Unit-style presentation tests for /api/auth/register.

These tests should isolate the route by monkeypatching `get_register_use_case`.
Tests use proper fake implementations of dependency interfaces.
"""

from typing import Optional

import pytest

from features.users.application.interfaces import (
    UserRepositoryInterface,
    PasswordHasherInterface,
)
from features.users.application.use_cases.auth_use_cases import RegisterCommand, RegisterUseCase
from features.users.domain.models.user import User, Role
from features.users.presentation.api import auth_routes
from shared.domain.exceptions import ValidationError


# Fake Implementations of Dependency Interfaces


class FakeUserRepository(UserRepositoryInterface):
    """Fake repository for testing."""

    def __init__(self):
        self.stored_users = {}
        self.next_id = 1

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.stored_users.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        for user in self.stored_users.values():
            if user.email == email:
                return user
        return None

    def save(self, user: User) -> User:
        if user.id is None:
            user.id = self.next_id
            self.next_id += 1
        self.stored_users[user.id] = user
        return user

    def delete(self, user_id: int) -> bool:
        if user_id in self.stored_users:
            del self.stored_users[user_id]
            return True
        return False

    def list_all(self):
        return list(self.stored_users.values())

    def list_by_role(self, role: str):
        return [u for u in self.stored_users.values() if u.role.value == role]


class FakePasswordHasher(PasswordHasherInterface):
    """Fake password hasher for testing."""

    def hash(self, password: str) -> str:
        return f"hashed_{password}"

    def verify(self, hashed: str, password: str) -> bool:
        return hashed == f"hashed_{password}"


# Tests


def test_register_returns_201_on_valid_payload(client, monkeypatch):
    """Test successful registration returns 201."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()

    def get_fake_use_case():
        return RegisterUseCase(fake_repo, fake_hasher)

    monkeypatch.setattr(auth_routes, "get_register_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/register",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass123",
            "phone": "12345678",
        },
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "User registered successfully"

    # Verify user was saved in repository
    saved_user = fake_repo.get_by_email("john@example.com")
    assert saved_user is not None
    assert saved_user.name == "John Doe"
    assert saved_user.phone == "12345678"
    assert saved_user.role == Role.CUSTOMER


def test_register_returns_400_for_invalid_json(client, monkeypatch):
    """Test register route returns 400 for invalid JSON."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()

    def get_fake_use_case():
        return RegisterUseCase(fake_repo, fake_hasher)

    monkeypatch.setattr(auth_routes, "get_register_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/register",
        data="invalid json {",
        content_type="application/json",
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Invalid JSON body"


def test_register_returns_400_for_schema_validation_error(client, monkeypatch):
    """Test register route returns 400 for missing required fields."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()

    def get_fake_use_case():
        return RegisterUseCase(fake_repo, fake_hasher)

    monkeypatch.setattr(auth_routes, "get_register_use_case", get_fake_use_case)

    # Missing required fields
    response = client.post(
        "/api/auth/register",
        json={
            "name": "John Doe",
            # Missing email and password
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Registration failed"
    assert "details" in data


def test_register_returns_409_on_duplicate_email(client, monkeypatch):
    """Test register route returns 409 when email already exists."""
    # Pre-populate repository with an existing user
    fake_repo = FakeUserRepository()
    existing_user = User(
        id=1,
        name="Existing User",
        email="existing@example.com",
        password_hash="hashed_password",
        role=Role.CUSTOMER,
    )
    fake_repo.save(existing_user)

    fake_hasher = FakePasswordHasher()

    def get_fake_use_case():
        return RegisterUseCase(fake_repo, fake_hasher)

    monkeypatch.setattr(auth_routes, "get_register_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/register",
        json={
            "name": "John Doe",
            "email": "existing@example.com",
            "password": "SecurePass123",
        },
    )

    assert response.status_code == 409
    data = response.get_json()
    assert data["error"] == "email already exists"


def test_register_with_valid_role(client, monkeypatch):
    """Test registering with a valid non-default role."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()

    def get_fake_use_case():
        return RegisterUseCase(fake_repo, fake_hasher)

    monkeypatch.setattr(auth_routes, "get_register_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Staff Member",
            "email": "staff@example.com",
            "password": "SecurePass123",
            "role": "staff",
        },
    )

    assert response.status_code == 201

    saved_user = fake_repo.get_by_email("staff@example.com")
    assert saved_user.role == Role.STAFF


def test_register_defaults_role_to_customer(client, monkeypatch):
    """Test that registration defaults role to customer when not specified."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()

    def get_fake_use_case():
        return RegisterUseCase(fake_repo, fake_hasher)

    monkeypatch.setattr(auth_routes, "get_register_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Customer User",
            "email": "customer@example.com",
            "password": "SecurePass123",
        },
    )

    assert response.status_code == 201

    saved_user = fake_repo.get_by_email("customer@example.com")
    assert saved_user.role == Role.CUSTOMER


def test_register_returns_400_for_invalid_email(client, monkeypatch):
    """Test register returns 400 for invalid email format."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()

    def get_fake_use_case():
        return RegisterUseCase(fake_repo, fake_hasher)

    monkeypatch.setattr(auth_routes, "get_register_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/register",
        json={
            "name": "John Doe",
            "email": "invalid-email",
            "password": "SecurePass123",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Registration failed"
    assert "details" in data


def test_register_returns_400_for_short_password(client, monkeypatch):
    """Test register returns 400 when password is too short."""
    fake_repo = FakeUserRepository()
    fake_hasher = FakePasswordHasher()

    def get_fake_use_case():
        return RegisterUseCase(fake_repo, fake_hasher)

    monkeypatch.setattr(auth_routes, "get_register_use_case", get_fake_use_case)

    response = client.post(
        "/api/auth/register",
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "Short1",  # Less than 8 characters
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == "Registration failed"
