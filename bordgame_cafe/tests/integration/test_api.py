"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAuthAPI:
    """Tests for authentication endpoints."""
    
    def test_register_user(self, client, test_user_data):
        """Test user registration endpoint."""
        response = client.post("/auth/register", json=test_user_data)
        # TODO: Implement assertions when endpoints are complete
        assert response.status_code in [200, 201, 400]
    
    def test_login(self, client):
        """Test login endpoint."""
        login_data = {
            "email": "test@example.com",
            "password": "testpassword123",
        }
        response = client.post("/auth/login", json=login_data)
        # TODO: Implement assertions when endpoints are complete
        assert response.status_code in [200, 401, 400]


class TestGamesAPI:
    """Tests for games endpoints."""
    
    def test_list_games(self, client):
        """Test listing games."""
        response = client.get("/games")
        assert response.status_code == 200
    
    def test_get_game(self, client):
        """Test getting a specific game."""
        response = client.get("/games/1")
        # TODO: Implement assertions when endpoints are complete
        assert response.status_code in [200, 404]


class TestTablesAPI:
    """Tests for tables endpoints."""
    
    def test_list_tables(self, client):
        """Test listing tables."""
        response = client.get("/tables")
        assert response.status_code == 200


class TestReservationsAPI:
    """Tests for reservations endpoints."""
    
    def test_list_reservations(self, client):
        """Test listing reservations."""
        response = client.get("/reservations")
        assert response.status_code == 200


class TestHealthCheck:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "app" in response.json()
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
