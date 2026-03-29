"""Unit tests for auth application use cases.

These tests define RegisterUseCase/LoginUseCase behavior directly,
independent of Flask routes and adapters.
"""

from unittest.mock import Mock

import pytest

from features.users.application.use_cases.auth_use_cases import (
    RegisterCommand,
    RegisterUseCase,
    LoginCommand,
    LoginUseCase,
)
from features.users.domain.models.user import User, Role
from shared.domain.exceptions import ValidationError


class TestRegisterUseCase:
    """Behavior specs for user registration."""

    def setup_method(self):
        self.mock_repo = Mock()
        self.mock_repo.save.side_effect = lambda user: user
        self.mock_hasher = Mock()
        self.use_case = RegisterUseCase(self.mock_repo, self.mock_hasher)

    def test_register_creates_user_with_hashed_password_and_default_role(self):
        cmd = RegisterCommand(
            name="Alice",
            email="alice@example.com",
            password="SecurePass123",
        )

        self.mock_repo.get_by_email.return_value = None
        self.mock_hasher.hash.return_value = "hashed_value"

        user = self.use_case.execute(cmd)

        assert user.name == "Alice"
        assert user.email == "alice@example.com"
        assert user.password_hash == "hashed_value"
        assert user.role == Role.CUSTOMER
        assert user.phone is None
        self.mock_repo.get_by_email.assert_called_once_with("alice@example.com")
        self.mock_hasher.hash.assert_called_once_with("SecurePass123")
        self.mock_repo.save.assert_called_once()

    def test_register_uses_explicit_role(self):
        cmd = RegisterCommand(
            name="Staff User",
            email="staff@example.com",
            password="SecurePass123",
            role="staff",
        )

        self.mock_repo.get_by_email.return_value = None
        self.mock_hasher.hash.return_value = "hashed_value"
        self.mock_repo.save.side_effect = lambda user: user

        user = self.use_case.execute(cmd)

        assert user.role == Role.STAFF

    def test_register_rejects_duplicate_email_without_saving(self):
        cmd = RegisterCommand(
            name="Dup",
            email="dup@example.com",
            password="SecurePass123",
        )
        self.mock_repo.get_by_email.return_value = User(
            name="Existing",
            email="dup@example.com",
            password_hash="hash",
            role=Role.CUSTOMER,
            id=9,
        )

        with pytest.raises(ValidationError, match="email already exists"):
            self.use_case.execute(cmd)

        self.mock_hasher.hash.assert_not_called()
        self.mock_repo.save.assert_not_called()


class TestLoginUseCase:
    """Behavior specs for user login."""

    def setup_method(self):
        self.mock_repo = Mock()
        self.mock_hasher = Mock()
        self.mock_session = Mock()
        self.use_case = LoginUseCase(self.mock_repo, self.mock_hasher, self.mock_session)

    def test_login_returns_user_and_starts_session_on_valid_credentials(self):
        user = User(
            id=7,
            name="Bob",
            email="bob@example.com",
            password_hash="hashed_pw",
            role=Role.CUSTOMER,
        )
        cmd = LoginCommand(email="bob@example.com", password="SecurePass123")

        self.mock_repo.get_by_email.return_value = user
        self.mock_hasher.verify.return_value = True

        result = self.use_case.execute(cmd)

        assert result is user
        self.mock_repo.get_by_email.assert_called_once_with("bob@example.com")
        self.mock_hasher.verify.assert_called_once_with("hashed_pw", "SecurePass123")
        self.mock_session.login.assert_called_once_with(7)

    def test_login_rejects_invalid_password_and_does_not_start_session(self):
        user = User(
            id=7,
            name="Bob",
            email="bob@example.com",
            password_hash="hashed_pw",
            role=Role.CUSTOMER,
        )
        cmd = LoginCommand(email="bob@example.com", password="WrongPassword")

        self.mock_repo.get_by_email.return_value = user
        self.mock_hasher.verify.return_value = False

        with pytest.raises(ValidationError, match="Invalid credentials"):
            self.use_case.execute(cmd)

        self.mock_session.login.assert_not_called()

    def test_login_rejects_unknown_email_without_password_check(self):
        cmd = LoginCommand(email="nobody@example.com", password="AnyPassword")

        self.mock_repo.get_by_email.return_value = None

        with pytest.raises(ValidationError, match="Invalid credentials"):
            self.use_case.execute(cmd)

        self.mock_hasher.verify.assert_not_called()
        self.mock_session.login.assert_not_called()
