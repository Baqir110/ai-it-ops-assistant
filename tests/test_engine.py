"""Tests for the anomaly detection engine."""

from app.engine.anomaly_detector import AnomalyDetector
from app.models.schemas import SystemTelemetry


def test_anomaly_detector_normal():
    """Test that normal telemetry produces no anomalies."""
    detector = AnomalyDetector()
    telemetry = SystemTelemetry(
        cpu_percent=25.0,
        ram_percent=40.0,
        disk_percent=50.0,
        services={"api": "RUNNING"},
        http_endpoints={"https://api.example.com/health": 200},
    )
    result = detector.evaluate(telemetry)
    assert result["has_anomalies"] is False
    assert result["anomaly_count"] == 0


def test_anomaly_detector_high_cpu():
    """Test that high CPU triggers an anomaly."""
    detector = AnomalyDetector()
    telemetry = SystemTelemetry(
        cpu_percent=96.0,
        ram_percent=40.0,
        disk_percent=50.0,
        services={},
        http_endpoints={},
    )
    result = detector.evaluate(telemetry)
    assert result["has_anomalies"] is True
    assert result["anomaly_count"] >= 1
    assert any("CPU" in a for a in result["anomalies"])


def test_anomaly_detector_service_outage():
    """Test that service outage is detected."""
    detector = AnomalyDetector()
    telemetry = SystemTelemetry(
        cpu_percent=30.0,
        ram_percent=40.0,
        disk_percent=50.0,
        services={"api": "DOWN"},
        http_endpoints={"https://api.example.com/health": 503},
    )
    result = detector.evaluate(telemetry)
    assert result["has_anomalies"] is True
    assert any("outage" in a.lower() for a in result["anomalies"])


def test_anomaly_detector_multiple_issues():
    """Test detection of multiple simultaneous anomalies."""
    detector = AnomalyDetector()
    telemetry = SystemTelemetry(
        cpu_percent=95.0,
        ram_percent=92.0,
        disk_percent=97.0,
        services={"api": "DOWN"},
        http_endpoints={"https://api.example.com/health": 503},
    )
    result = detector.evaluate(telemetry)
    assert result["has_anomalies"] is True
    assert result["anomaly_count"] >= 3
