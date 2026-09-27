"""Tests for the OpsGuard API."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def auth_token():
    """Get an auth token for API calls."""
    import uuid
    username = f"apiuser_{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "SecurePassword123!",
            "role": "admin",
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_telemetry_analysis_critical_incident(auth_token):
    """Test telemetry analysis with critical values."""
    payload = {
        "cpu_percent": 94.0,
        "ram_percent": 91.0,
        "disk_percent": 97.0,
        "services": {
            "apache2": "DOWN",
        },
        "http_endpoints": {
            "https://app.internal/health": 503,
        },
    }

    response = client.post(
        "/api/v1/telemetry/analyze",
        json=payload,
        headers=auth_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert data["analysis_method"] == "RULE_BASED"
    assert len(data["recommended_actions"]) > 0


def test_telemetry_analysis_healthy_system(auth_token):
    """Test telemetry analysis with healthy values."""
    payload = {
        "cpu_percent": 25.0,
        "ram_percent": 40.0,
        "disk_percent": 50.0,
        "services": {
            "apache2": "RUNNING",
        },
        "http_endpoints": {
            "https://app.internal/health": 200,
        },
    }

    response = client.post(
        "/api/v1/telemetry/analyze",
        json=payload,
        headers=auth_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["severity"] == "LOW"
    assert data["incident_title"] == "System Health Normal"
    assert data["escalation_required"] is False


def test_high_cpu_incident(auth_token):
    """Test high CPU detection."""
    payload = {
        "cpu_percent": 96.0,
        "ram_percent": 40.0,
        "disk_percent": 50.0,
        "services": {},
        "http_endpoints": {},
    }

    response = client.post(
        "/api/v1/telemetry/analyze",
        json=payload,
        headers=auth_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert "CPU" in data["likely_cause"] or "cpu" in data["likely_cause"].lower()
    assert len(data["recommended_actions"]) > 0


def test_high_memory_incident(auth_token):
    """Test high memory detection."""
    payload = {
        "cpu_percent": 30.0,
        "ram_percent": 92.0,
        "disk_percent": 50.0,
        "services": {},
        "http_endpoints": {},
    }

    response = client.post(
        "/api/v1/telemetry/analyze",
        json=payload,
        headers=auth_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["severity"] in ["MEDIUM", "HIGH", "CRITICAL"]
    assert "RAM" in data["likely_cause"] or "memory" in data["likely_cause"].lower()
    assert len(data["recommended_actions"]) > 0


def test_service_outage_incident(auth_token):
    """Test service outage detection."""
    payload = {
        "cpu_percent": 30.0,
        "ram_percent": 40.0,
        "disk_percent": 50.0,
        "services": {
            "apache2": "DOWN",
        },
        "http_endpoints": {
            "https://app.internal/health": 503,
        },
    }

    response = client.post(
        "/api/v1/telemetry/analyze",
        json=payload,
        headers=auth_token,
    )

    assert response.status_code == 200

    data = response.json()

    assert "Service outage" in data["likely_cause"] or "outage" in data["likely_cause"].lower()
    assert len(data["recommended_actions"]) > 0


def test_incidents_are_persisted(auth_token):
    """Test that incidents are saved to the database."""
    payload = {
        "cpu_percent": 88.0,
        "ram_percent": 70.0,
        "disk_percent": 60.0,
        "services": {},
        "http_endpoints": {},
    }

    create_response = client.post(
        "/api/v1/telemetry/analyze",
        json=payload,
        headers=auth_token,
    )

    assert create_response.status_code == 200

    incidents_response = client.get(
        "/api/v1/incidents",
        headers=auth_token,
    )

    assert incidents_response.status_code == 200

    data = incidents_response.json()

    assert len(data) > 0


def test_create_incident_api(auth_token):
    """Test creating an incident via the API."""
    response = client.post(
        "/api/v1/incidents",
        json={
            "title": "Test Incident",
            "severity": "HIGH",
            "description": "Test description",
            "source": "test",
        },
        headers=auth_token,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Incident"
    assert data["severity"] == "HIGH"
    assert data["status"] == "DETECTED"


def test_list_services(auth_token):
    """Test listing services."""
    response = client.get("/api/v1/services", headers=auth_token)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_remediation_actions(auth_token):
    """Test listing available remediation actions."""
    response = client.get("/api/v1/remediation/actions", headers=auth_token)
    assert response.status_code == 200
    actions = response.json()
    assert len(actions) > 0
    assert any(a["action_type"] == "restart_service" for a in actions)


def test_sre_summary(auth_token):
    """Test SRE summary endpoint."""
    response = client.get("/api/v1/slo/summary", headers=auth_token)
    assert response.status_code == 200
    data = response.json()
    assert "availability_24h" in data
    assert "mttr_minutes" in data


def test_cost_recommendations(auth_token):
    """Test cost recommendations endpoint."""
    response = client.get("/api/v1/cost/recommendations", headers=auth_token)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
