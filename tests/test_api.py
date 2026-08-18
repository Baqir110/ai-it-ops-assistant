from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_telemetry_analysis_critical_incident():
    payload = {
        "cpu_percent": 94.0,
        "ram_percent": 91.0,
        "disk_percent": 97.0,
        "services": {"apache2": "DOWN"},
        "http_endpoints": {"https://app.internal/health": 503},
    }
    response = client.post("/api/v1/telemetry/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "CRITICAL"
    assert "apache2" in data["likely_cause"]
    assert len(data["recommended_actions"]) > 0


def test_telemetry_analysis_healthy_system():
    payload = {
        "cpu_percent": 25.0,
        "ram_percent": 40.0,
        "disk_percent": 50.0,
        "services": {"apache2": "UP"},
        "http_endpoints": {"https://app.internal/health": 200},
    }
    response = client.post("/api/v1/telemetry/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "LOW"
    assert data["escalation_required"] is False
