"""Unit tests for use cases."""

import pytest
from datetime import datetime, timedelta
from domain.models import User, UserRole, Reservation, ReservationStatus, Table
from domain.exceptions import (
    UserAlreadyExists,
    UserNotFound,
    ReservationNotFound,
    TableNotFound,
    PartyTooLarge,
    OverlappingReservation,
)


class TestUserUseCases:
    """Tests for user-related use cases."""
    
    @pytest.mark.asyncio
    async def test_register_customer_success(self, test_user_data):
        """Test successful customer registration."""
        # TODO: Implement when repository mocks are ready
        pass
    
    @pytest.mark.asyncio
    async def test_register_duplicate_user(self, test_user_data):
        """Test registering a user with an existing email."""
        # TODO: Implement when repository mocks are ready
        pass


class TestReservationUseCases:
    """Tests for reservation-related use cases."""
    
    @pytest.mark.asyncio
    async def test_create_reservation_success(self, test_user_data, test_table_data):
        """Test successful reservation creation."""
        # TODO: Implement when repository mocks are ready
        pass
    
    @pytest.mark.asyncio
    async def test_create_reservation_party_too_large(self):
        """Test creating reservation with party size exceeding capacity."""
        # TODO: Implement when repository mocks are ready
        pass
    
    @pytest.mark.asyncio
    async def test_create_reservation_overlapping(self):
        """Test creating overlapping reservations."""
        # TODO: Implement when repository mocks are ready
        pass
