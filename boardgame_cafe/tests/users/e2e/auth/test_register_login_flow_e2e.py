"""E2E auth flow tests for register/login.

These should validate the full user journey using the app as a black box.
"""

def test_user_can_register_then_login_then_access_me_then_log_out(client):
    """Test complete user auth flow: register -> login -> access /me -> logout."""
    
    # Step 1: Register a new user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "E2E Test User",
            "email": "e2e-test@example.com",
            "password": "E2ETestPassword123",
            "phone": "555-E2E00",
        },
    )
    
    assert register_response.status_code == 201
    data = register_response.get_json()
    assert data["message"] == "User registered successfully"
    
    # Step 2: Login with the registered credentials
    login_response = client.post(
        "/auth/login",
        json={
            "email": "e2e-test@example.com",
            "password": "E2ETestPassword123",
        },
    )
    
    assert login_response.status_code == 200
    login_data = login_response.get_json()
    assert login_data["message"] == "Logged in"
    assert login_data["user"]["email"] == "e2e-test@example.com"
    assert login_data["user"]["name"] == "E2E Test User"
    assert login_data["user"]["id"] is not None
    
    # Step 3: Access the /me endpoint to confirm logged in
    me_response = client.get("/auth/me")
    
    assert me_response.status_code == 200
    me_data = me_response.get_json()
    assert me_data["user"]["email"] == "e2e-test@example.com"
    assert me_data["user"]["name"] == "E2E Test User"
    assert me_data["user"]["phone"] == "555-E2E00"
    
    # Step 4: Logout
    logout_response = client.post("/auth/logout")
    
    assert logout_response.status_code == 200
    logout_data = logout_response.get_json()
    assert logout_data["message"] == "Logged out"
    
    # Step 5: Verify /me is not accessible after logout
    me_after_logout = client.get("/auth/me")
    
    assert me_after_logout.status_code == 401


def test_multiple_users_can_register_and_login_separately(client):
    """Test that multiple users can register and login independently."""
    
    # Register user 1
    user1_response = client.post(
        "/auth/register",
        json={
            "name": "User One",
            "email": "user1@example.com",
            "password": "Password1234",
        },
    )
    assert user1_response.status_code == 201
    
    # Register user 2
    user2_response = client.post(
        "/auth/register",
        json={
            "name": "User Two",
            "email": "user2@example.com",
            "password": "Password5678",
        },
    )
    assert user2_response.status_code == 201
    
    # Login as user 1
    login1_response = client.post(
        "/auth/login",
        json={
            "email": "user1@example.com",
            "password": "Password1234",
        },
    )
    assert login1_response.status_code == 200
    user1_data = login1_response.get_json()["user"]
    
    # Verify /me returns user 1
    me1_response = client.get("/auth/me")
    assert me1_response.status_code == 200
    assert me1_response.get_json()["user"]["name"] == "User One"
    
    # Logout user 1
    client.post("/auth/logout")
    
    # Login as user 2
    login2_response = client.post(
        "/auth/login",
        json={
            "email": "user2@example.com",
            "password": "Password5678",
        },
    )
    assert login2_response.status_code == 200
    user2_data = login2_response.get_json()["user"]
    
    # Verify /me returns user 2 now
    me2_response = client.get("/auth/me")
    assert me2_response.status_code == 200
    assert me2_response.get_json()["user"]["name"] == "User Two"
    assert user1_data["id"] != user2_data["id"]
