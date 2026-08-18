from app.models.telemetry import TelemetryPayload
from app.engine.rules import evaluate_telemetry


def test_evaluate_telemetry_normal():
    payload = TelemetryPayload(
        service_name="auth-service",
        metric_type="memory_usage",
        metric_value=45.0,
        threshold=80.0,
        status="ok",
    )
    result = evaluate_telemetry(payload)
    assert result is None


def test_evaluate_telemetry_trigger():
    payload = TelemetryPayload(
        service_name="database-replica",
        metric_type="disk_usage",
        metric_value=95.0,
        threshold=80.0,
        status="critical",
    )
    result = evaluate_telemetry(payload)
    assert result is not None
    assert result.severity == "CRITICAL"
    assert result.service_name == "database-replica"
    assert len(result.triggered_rules) >= 1
