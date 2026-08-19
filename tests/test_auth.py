from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_register_user():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testoperator",
            "email": "operator@example.com",
            "password": "SecurePassword123!",
            "role": "operator",
        },
    )
    assert response.status_code == 201
    assert "created successfully" in response.json()["message"]


def test_login_success():
    # First register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "authuser",
            "email": "auth@example.com",
            "password": "MySecretPassword123!",
            "role": "admin",
        },
    )

    # Attempt login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "authuser", "password": "MySecretPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_get_current_user_authenticated():
    # Register and login to get token
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "meuser",
            "email": "me@example.com",
            "password": "MySecretPassword123!",
            "role": "viewer",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": "meuser", "password": "MySecretPassword123!"},
    )
    token = login_res.json()["access_token"]

    # Access /users/me
    response = client.get(
        "/api/v1/auth/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "meuser"


def test_protected_endpoint_unauthorized():
    # Access endpoint without token
    response = client.get("/api/v1/auth/users/me")
    assert response.status_code == 401
