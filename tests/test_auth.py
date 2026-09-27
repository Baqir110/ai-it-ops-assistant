"""Tests for authentication system."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_user():
    """Ensure a test user exists before each test."""
    # Register a unique user for each test
    import uuid

    username = f"testuser_{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "SecurePassword123!",
            "role": "admin",
        },
    )
    return username


def test_register_user(setup_user):
    """Test user registration."""
    import uuid

    username = f"newuser_{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "SecurePassword123!",
            "role": "operator",
        },
    )
    assert response.status_code == 201
    assert "created successfully" in response.json()["message"]


def test_login_success(setup_user):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": setup_user, "password": "SecurePassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent_user_xyz", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_get_current_user_authenticated(setup_user):
    """Test accessing protected endpoint with valid token."""
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": setup_user, "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/api/v1/auth/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == setup_user


def test_protected_endpoint_unauthorized():
    """Test accessing protected endpoint without token."""
    response = client.get("/api/v1/auth/users/me")
    assert response.status_code == 401
