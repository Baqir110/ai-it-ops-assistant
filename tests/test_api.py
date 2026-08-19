from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200


def test_telemetry_analysis_critical_incident():
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
    )

    assert response.status_code == 200

    data = response.json()

    assert data["severity"] == "CRITICAL"
    assert data["analysis_method"] == "RULE_BASED"
    assert len(data["recommended_actions"]) > 0
    assert len(data["sources_consulted"]) > 0


def test_telemetry_analysis_healthy_system():
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
    )

    assert response.status_code == 200

    data = response.json()

    assert data["severity"] == "LOW"
    assert data["incident_title"] == "System Health Normal"
    assert data["escalation_required"] is False


def test_high_cpu_incident():
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
    )

    assert response.status_code == 200

    data = response.json()

    assert data["severity"] in ["HIGH", "CRITICAL"]
    assert "CPU" in data["likely_cause"]
    assert len(data["recommended_actions"]) > 0


def test_high_memory_incident():
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
    )

    assert response.status_code == 200

    data = response.json()

    assert data["severity"] in ["MEDIUM", "HIGH", "CRITICAL"]
    assert "RAM" in data["likely_cause"]
    assert len(data["recommended_actions"]) > 0


def test_service_outage_incident():
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
    )

    assert response.status_code == 200

    data = response.json()

    assert "Service outage" in data["likely_cause"]
    assert len(data["recommended_actions"]) > 0


def test_incidents_are_persisted():
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
    )

    assert create_response.status_code == 200

    incidents_response = client.get(
        "/api/v1/incidents",
    )

    assert incidents_response.status_code == 200

    data = incidents_response.json()

    assert data["Count"] > 0
    assert len(data["value"]) > 0
