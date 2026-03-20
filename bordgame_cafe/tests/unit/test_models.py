"""Unit tests for user models and use cases."""

import pytest
from domain.models import User, UserRole
from domain.exceptions import UserAlreadyExists, UserNotFound


class TestUserModel:
    """Tests for User model."""
    
    def test_create_user(self, test_user_data):
        """Test creating a user."""
        user = User(**test_user_data)
        
        assert user.email == test_user_data["email"]
        assert user.full_name == test_user_data["full_name"]
        assert user.role == UserRole.CUSTOMER
    
    def test_user_string_representation(self, test_user_data):
        """Test user string representation."""
        user = User(**test_user_data)
        
        assert str(user) == f"{test_user_data['full_name']} <{test_user_data['email']}>"
