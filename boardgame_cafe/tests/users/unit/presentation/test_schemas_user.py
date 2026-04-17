"""Unit tests for user response and update schemas.

These tests validate UserUpdate and UserResponse parsing and validation behavior.
Uses TDD approach - schemas should fit the tests, not vice versa.
"""

import pytest
from pydantic import ValidationError

from features.users.domain.models.user import User, Role
from features.users.presentation.schemas.user_schema import UserUpdate, UserResponse


class TestUserUpdate:
    """Test suite for UserUpdate schema validation."""

    def test_user_update_accepts_all_optional_fields(self):
        """All fields in UserUpdate are optional, so empty dict should pass."""
        payload = {}
        user_update = UserUpdate.model_validate(payload)
        assert user_update.name is None
        assert user_update.phone is None
        assert user_update.role is None

    def test_user_update_accepts_name_only(self):
        """Should accept updating only the name field."""
        payload = {"name": "Updated Name"}
        user_update = UserUpdate.model_validate(payload)
        assert user_update.name == "Updated Name"
        assert user_update.phone is None
        assert user_update.role is None

    def test_user_update_accepts_phone_only(self):
        """Should accept updating only the phone field."""
        payload = {"phone": "555-9999"}
        user_update = UserUpdate.model_validate(payload)
        assert user_update.name is None
        assert user_update.phone == "555-9999"
        assert user_update.role is None

    def test_user_update_accepts_role_only(self):
        """Should accept updating only the role field."""
        payload = {"role": "staff"}
        user_update = UserUpdate.model_validate(payload)
        assert user_update.name is None
        assert user_update.phone is None
        assert user_update.role == "staff"

    def test_user_update_accepts_all_fields(self):
        """Should accept updating all fields at once."""
        payload = {
            "name": "New Name",
            "phone": "555-1111",
            "role": "admin",
        }
        user_update = UserUpdate.model_validate(payload)
        assert user_update.name == "New Name"
        assert user_update.phone == "555-1111"
        assert user_update.role == "admin"

    def test_user_update_accepts_valid_roles(self):
        """Valid roles should be accepted."""
        for role in ["customer", "staff", "admin"]:
            payload = {"role": role}
            user_update = UserUpdate.model_validate(payload)
            assert user_update.role == role

    def test_user_update_rejects_invalid_role(self):
        """Invalid role should raise ValidationError."""
        payload = {"role": "superuser"}
        with pytest.raises(ValidationError):
            UserUpdate.model_validate(payload)

    def test_user_update_rejects_empty_name(self):
        """Empty name string should raise ValidationError."""
        payload = {"name": ""}
        with pytest.raises(ValidationError):
            UserUpdate.model_validate(payload)

    def test_user_update_rejects_whitespace_only_name(self):
        """Whitespace-only name should be stripped and rejected."""
        payload = {"name": "   "}
        with pytest.raises(ValidationError):
            UserUpdate.model_validate(payload)

    def test_user_update_strips_name_whitespace(self):
        """Name with leading/trailing whitespace should be stripped."""
        payload = {"name": "  Updated Name  "}
        user_update = UserUpdate.model_validate(payload)
        assert user_update.name == "Updated Name"

    def test_user_update_rejects_name_exceeding_max_length(self):
        """Name exceeding 100 characters should raise ValidationError."""
        payload = {"name": "A" * 101}
        with pytest.raises(ValidationError):
            UserUpdate.model_validate(payload)

    def test_user_update_accepts_name_at_max_length(self):
        """Name with exactly 100 characters should be accepted."""
        payload = {"name": "A" * 100}
        user_update = UserUpdate.model_validate(payload)
        assert len(user_update.name) == 100

    def test_user_update_accepts_empty_phone_as_none(self):
        """Empty phone string should be normalized to None."""
        payload = {"phone": ""}
        user_update = UserUpdate.model_validate(payload)
        assert user_update.phone is None

    def test_user_update_accepts_whitespace_only_phone_as_none(self):
        """Whitespace-only phone should be normalized to None."""
        payload = {"phone": "   "}
        user_update = UserUpdate.model_validate(payload)
        assert user_update.phone is None

    def test_user_update_strips_phone_whitespace(self):
        """Phone with leading/trailing whitespace should be stripped."""
        payload = {"phone": "  555-5555  "}
        user_update = UserUpdate.model_validate(payload)
        assert user_update.phone == "555-5555"

    def test_user_update_rejects_phone_exceeding_max_length(self):
        """Phone exceeding 20 characters should raise ValidationError."""
        payload = {"phone": "1" * 21}
        with pytest.raises(ValidationError):
            UserUpdate.model_validate(payload)

    def test_user_update_accepts_phone_at_max_length(self):
        """Phone with exactly 20 characters should be accepted."""
        payload = {"phone": "1" * 20}
        user_update = UserUpdate.model_validate(payload)
        assert len(user_update.phone) == 20


class TestUserResponse:
    """Test suite for UserResponse schema validation."""

    def test_user_response_accepts_valid_payload(self):
        """Valid user response payload should pass validation."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "role": "customer",
            "force_password_change": False,
        }
        response = UserResponse.model_validate(payload)
        assert response.id == 1
        assert response.name == "John Doe"
        assert response.email == "john@example.com"
        assert response.phone == "555-1234"
        assert response.role == "customer"
        assert response.force_password_change is False

    def test_user_response_phone_is_optional(self):
        """Phone should be optional in user response."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "customer",
            "force_password_change": False,
        }
        response = UserResponse.model_validate(payload)
        assert response.phone is None

    def test_user_response_rejects_missing_id(self):
        """Missing id should raise ValidationError."""
        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "role": "customer",
            "force_password_change": False,
        }
        with pytest.raises(ValidationError) as exc_info:
            UserResponse.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "id" for e in errors)

    def test_user_response_rejects_missing_name(self):
        """Missing name should raise ValidationError."""
        payload = {
            "id": 1,
            "email": "john@example.com",
            "role": "customer",
            "force_password_change": False,
        }
        with pytest.raises(ValidationError) as exc_info:
            UserResponse.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "name" for e in errors)

    def test_user_response_rejects_missing_email(self):
        """Missing email should raise ValidationError."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "role": "customer",
            "force_password_change": False,
        }
        with pytest.raises(ValidationError) as exc_info:
            UserResponse.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "email" for e in errors)

    def test_user_response_rejects_invalid_email(self):
        """Invalid email format should raise ValidationError."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "invalid-email",
            "role": "customer",
            "force_password_change": False,
        }
        with pytest.raises(ValidationError):
            UserResponse.model_validate(payload)

    def test_user_response_rejects_missing_role(self):
        """Missing role should raise ValidationError."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "force_password_change": False,
        }
        with pytest.raises(ValidationError) as exc_info:
            UserResponse.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "role" for e in errors)

    def test_user_response_rejects_missing_force_password_change(self):
        """Missing force_password_change should raise ValidationError."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "customer",
        }
        with pytest.raises(ValidationError) as exc_info:
            UserResponse.model_validate(payload)
        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "force_password_change" for e in errors)

    def test_user_response_from_domain_converts_user(self):
        """from_domain should correctly convert domain User to UserResponse."""
        user = User(
            id=1,
            name="John Doe",
            email="john@example.com",
            password_hash="hashed_password",
            role=Role.STAFF,
            phone="555-1234",
            force_password_change=True,
        )
        response = UserResponse.from_domain(user)
        assert response.id == 1
        assert response.name == "John Doe"
        assert response.email == "john@example.com"
        assert response.phone == "555-1234"
        assert response.role == "staff"  # Should be string value
        assert response.force_password_change is True

    def test_user_response_from_domain_with_no_phone(self):
        """from_domain should handle User without phone."""
        user = User(
            id=2,
            name="Jane Doe",
            email="jane@example.com",
            password_hash="hashed_password",
            role=Role.CUSTOMER,
            force_password_change=False,
        )
        response = UserResponse.from_domain(user)
        assert response.phone is None

    def test_user_response_handles_different_roles(self):
        """from_domain should correctly convert all role types."""
        for role in [Role.CUSTOMER, Role.STAFF, Role.ADMIN]:
            user = User(
                id=1,
                name="Test User",
                email="test@example.com",
                password_hash="hashed_password",
                role=role,
                force_password_change=False,
            )
            response = UserResponse.from_domain(user)
            assert response.role == role.value

    def test_user_response_rejects_invalid_role_string(self):
        """Invalid role string should raise ValidationError."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "invalid_role",
            "force_password_change": False,
        }
        with pytest.raises(ValidationError):
            UserResponse.model_validate(payload)

    def test_user_response_accepts_valid_roles(self):
        """All valid roles should be accepted."""
        for role_str in ["customer", "staff", "admin"]:
            payload = {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "role": role_str,
                "force_password_change": False,
            }
            response = UserResponse.model_validate(payload)
            assert response.role == role_str

    def test_user_response_accepts_force_password_change_true(self):
        """force_password_change should accept True."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "customer",
            "force_password_change": True,
        }
        response = UserResponse.model_validate(payload)
        assert response.force_password_change is True

    def test_user_response_accepts_force_password_change_false(self):
        """force_password_change should accept False."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "customer",
            "force_password_change": False,
        }
        response = UserResponse.model_validate(payload)
        assert response.force_password_change is False

    def test_user_response_model_dump(self):
        """UserResponse should support model_dump for serialization."""
        payload = {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-1234",
            "role": "customer",
            "force_password_change": False,
        }
        response = UserResponse.model_validate(payload)
        dumped = response.model_dump()
        assert dumped["id"] == 1
        assert dumped["name"] == "John Doe"
        assert dumped["email"] == "john@example.com"
        assert dumped["phone"] == "555-1234"
        assert dumped["role"] == "customer"
        assert dumped["force_password_change"] is False
