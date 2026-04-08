"""Unit tests for auth request schemas.

These tests validate LoginRequest/UserCreate parsing and validation behavior.
Uses TDD approach - schemas should fit the tests, not vice versa.
"""

import pytest
from pydantic import ValidationError

from features.users.presentation.schemas.auth_schema import LoginRequest
from features.users.presentation.schemas.user_schema import UserCreate


class TestLoginRequest:
    """Test suite for LoginRequest schema validation."""

    def test_login_request_accepts_valid_payload(self):
        """Valid email and password should pass validation."""
        payload = {
            "email": "user@example.com",
            "password": "ValidPassword123",
        }
        request = LoginRequest.model_validate(payload)
        assert request.email == "user@example.com"
        assert request.password == "ValidPassword123"

    def test_login_request_rejects_invalid_email_format(self):
        """Invalid email format should raise ValidationError."""
        payload = {
            "email": "invalid-email",
            "password": "ValidPassword123",
        }
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "email" for e in errors)

    def test_login_request_rejects_missing_email(self):
        """Missing email should raise ValidationError."""
        payload = {
            "password": "ValidPassword123",
        }
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "email" for e in errors)

    def test_login_request_rejects_missing_password(self):
        """Missing password should raise ValidationError."""
        payload = {
            "email": "user@example.com",
        }
        with pytest.raises(ValidationError) as exc_info:
            LoginRequest.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "password" for e in errors)

    def test_login_request_rejects_empty_password(self):
        """Empty password should raise ValidationError."""
        payload = {
            "email": "user@example.com",
            "password": "",
        }
        with pytest.raises(ValidationError):
            LoginRequest.model_validate(payload)

    def test_login_request_rejects_email_with_no_domain(self):
        """Email without domain should raise ValidationError."""
        payload = {
            "email": "user@",
            "password": "ValidPassword123",
        }
        with pytest.raises(ValidationError):
            LoginRequest.model_validate(payload)

    def test_login_request_rejects_email_with_no_local_part(self):
        """Email without local part should raise ValidationError."""
        payload = {
            "email": "@example.com",
            "password": "ValidPassword123",
        }
        with pytest.raises(ValidationError):
            LoginRequest.model_validate(payload)


class TestUserCreate:
    """Test suite for UserCreate schema validation."""

    def test_register_payload_accepts_valid_input(self):
        """Valid registration payload should pass validation."""
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "password": "SecurePass123",
            "phone": "555-1234",
        }
        user = UserCreate.model_validate(payload)
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.password == "SecurePass123"
        assert user.phone == "555-1234"
        assert user.role == "customer"  # Default role

    def test_register_payload_defaults_role_to_customer(self):
        """When role is not provided, should default to 'customer'."""
        payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "SecurePass123",
        }
        user = UserCreate.model_validate(payload)
        assert user.role == "customer"

    def test_register_payload_accepts_valid_roles(self):
        """Valid roles (customer, staff, admin) should be accepted."""
        for role in ["customer", "staff", "admin"]:
            payload = {
                "name": "Test User",
                "email": f"user-{role}@example.com",
                "password": "SecurePass123",
                "role": role,
            }
            user = UserCreate.model_validate(payload)
            assert user.role == role

    def test_register_payload_rejects_invalid_role(self):
        """Invalid role should raise ValidationError."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "SecurePass123",
            "role": "superadmin",  # Invalid role
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "role" for e in errors)

    def test_register_payload_rejects_short_password(self):
        """Password shorter than 8 characters should raise ValidationError."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "Short1",  # 6 characters, needs 8+
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "password" for e in errors)

    def test_register_payload_accepts_exactly_8_char_password(self):
        """Password with exactly 8 characters should be accepted."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "12345678",
        }
        user = UserCreate.model_validate(payload)
        assert user.password == "12345678"

    def test_register_payload_rejects_empty_password(self):
        """Empty password should raise ValidationError."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "",
        }
        with pytest.raises(ValidationError):
            UserCreate.model_validate(payload)

    def test_register_payload_rejects_missing_name(self):
        """Missing name should raise ValidationError."""
        payload = {
            "email": "user@example.com",
            "password": "SecurePass123",
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "name" for e in errors)

    def test_register_payload_rejects_empty_name(self):
        """Empty name should raise ValidationError."""
        payload = {
            "name": "",
            "email": "user@example.com",
            "password": "SecurePass123",
        }
        with pytest.raises(ValidationError):
            UserCreate.model_validate(payload)

    def test_register_payload_rejects_whitespace_only_name(self):
        """Whitespace-only name should be stripped and rejected."""
        payload = {
            "name": "   ",
            "email": "user@example.com",
            "password": "SecurePass123",
        }
        with pytest.raises(ValidationError):
            UserCreate.model_validate(payload)

    def test_register_payload_strips_name_whitespace(self):
        """Name with leading/trailing whitespace should be stripped."""
        payload = {
            "name": "  John Doe  ",
            "email": "user@example.com",
            "password": "SecurePass123",
        }
        user = UserCreate.model_validate(payload)
        assert user.name == "John Doe"

    def test_register_payload_rejects_name_exceeding_max_length(self):
        """Name exceeding 100 characters should raise ValidationError."""
        payload = {
            "name": "A" * 101,
            "email": "user@example.com",
            "password": "SecurePass123",
        }
        with pytest.raises(ValidationError):
            UserCreate.model_validate(payload)

    def test_register_payload_accepts_name_at_max_length(self):
        """Name with exactly 100 characters should be accepted."""
        payload = {
            "name": "A" * 100,
            "email": "user@example.com",
            "password": "SecurePass123",
        }
        user = UserCreate.model_validate(payload)
        assert len(user.name) == 100

    def test_register_payload_rejects_invalid_email(self):
        """Invalid email format should raise ValidationError."""
        invalid_emails = [
            "notanemail",
            "missing@domain",
            "@nodomain.com",
            "spaces in@email.com",
        ]
        for invalid_email in invalid_emails:
            payload = {
                "name": "Test User",
                "email": invalid_email,
                "password": "SecurePass123",
            }
            with pytest.raises(ValidationError):
                UserCreate.model_validate(payload)

    def test_register_payload_phone_is_optional(self):
        """Phone number should be optional."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "SecurePass123",
        }
        user = UserCreate.model_validate(payload)
        assert user.phone is None

    def test_register_payload_accepts_valid_phone(self):
        """Valid phone number should be accepted."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "SecurePass123",
            "phone": "555-1234",
        }
        user = UserCreate.model_validate(payload)
        assert user.phone == "555-1234"

    def test_register_payload_converts_empty_phone_to_none(self):
        """Empty phone string should be treated as missing optional field."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "SecurePass123",
            "phone": "",
        }
        user = UserCreate.model_validate(payload)
        assert user.phone is None

    def test_register_payload_converts_whitespace_phone_to_none(self):
        """Whitespace-only phone should be treated as missing optional field."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "SecurePass123",
            "phone": "   ",
        }
        user = UserCreate.model_validate(payload)
        assert user.phone is None

    def test_register_payload_strips_phone_whitespace(self):
        """Phone with leading/trailing whitespace should be stripped."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "SecurePass123",
            "phone": "  555-1234  ",
        }
        user = UserCreate.model_validate(payload)
        assert user.phone == "555-1234"

    def test_register_payload_rejects_phone_exceeding_max_length(self):
        """Phone exceeding 20 characters should raise ValidationError."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "SecurePass123",
            "phone": "1" * 21,
        }
        with pytest.raises(ValidationError):
            UserCreate.model_validate(payload)

    def test_register_payload_accepts_phone_at_max_length(self):
        """Phone with exactly 20 characters should be accepted."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "SecurePass123",
            "phone": "1" * 20,
        }
        user = UserCreate.model_validate(payload)
        assert len(user.phone) == 20

    def test_register_payload_strips_password_whitespace(self):
        """Password with leading/trailing whitespace should be stripped."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
            "password": "  SecurePass123  ",
        }
        user = UserCreate.model_validate(payload)
        assert user.password == "SecurePass123"

    def test_register_payload_rejects_missing_email(self):
        """Missing email should raise ValidationError."""
        payload = {
            "name": "Test User",
            "password": "SecurePass123",
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "email" for e in errors)

    def test_register_payload_rejects_missing_password(self):
        """Missing password should raise ValidationError."""
        payload = {
            "name": "Test User",
            "email": "user@example.com",
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "password" for e in errors)
