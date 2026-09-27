"""Integration tests for OpsGuard — detectors, diagnosis, remediation, SLO."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def auth_token():
    """Get an auth token for API calls."""
    import uuid

    username = f"integuser_{uuid.uuid4().hex[:8]}"
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


class TestDetectionEngine:
    """Test the detection engine components."""

    def test_detector_registry(self):
        """Test that detectors are properly registered."""
        from app.detection.base import DetectorRegistry
        from app.detection.http_health import HTTPHealthDetector
        from app.detection.prometheus import PrometheusDetector

        registry = DetectorRegistry()
        registry.register(HTTPHealthDetector(lambda: None))
        registry.register(PrometheusDetector())

        assert "http_health" in registry.list_detectors()
        assert "prometheus" in registry.list_detectors()

    def test_detection_event_format(self):
        """Test standardized detection event format."""
        from app.detection.base import DetectionEvent

        event = DetectionEvent(
            source="test",
            type="test_event",
            severity="HIGH",
            message="Test detection",
            service="test-service",
            value=95.0,
            threshold=90.0,
        )

        data = event.to_dict()
        assert data["source"] == "test"
        assert data["type"] == "test_event"
        assert data["severity"] == "HIGH"
        assert data["value"] == 95.0
        assert data["threshold"] == 90.0


class TestIncidentLifecycle:
    """Test incident lifecycle state machine."""

    def test_valid_transitions(self):
        """Test valid state transitions."""
        from app.domain.incidents import can_transition

        assert can_transition("DETECTED", "INVESTIGATING")
        assert can_transition("INVESTIGATING", "DIAGNOSED")
        assert can_transition("DIAGNOSED", "ACTION_REQUIRED")
        assert can_transition("ACTION_REQUIRED", "REMEDIATING")
        assert can_transition("REMEDIATING", "VERIFYING")
        assert can_transition("VERIFYING", "RESOLVED")
        assert can_transition("RESOLVED", "CLOSED")

    def test_invalid_transitions(self):
        """Test invalid state transitions."""
        from app.domain.incidents import can_transition

        assert not can_transition("CLOSED", "DETECTED")
        assert not can_transition("RESOLVED", "INVESTIGATING")
        assert not can_transition("RESOLVED", "REMEDIATING")
        assert not can_transition("CLOSED", "INVESTIGATING")

    def test_terminal_states(self):
        """Test terminal states."""
        from app.domain.incidents import is_open

        assert not is_open("RESOLVED")
        assert not is_open("CLOSED")
        assert is_open("DETECTED")
        assert is_open("INVESTIGATING")
        assert is_open("REMEDIATING")


class TestDiagnosisEngine:
    """Test the diagnosis engine."""

    def test_runbook_mapping(self):
        """Test runbook key mapping for incident types."""
        from app.diagnosis.engine import RUNBOOK_MAP

        assert RUNBOOK_MAP["cpu_high"] == "cpu_high"
        assert RUNBOOK_MAP["memory_high"] == "memory_pressure"
        assert RUNBOOK_MAP["http_health_failure"] == "service_outage"
        assert RUNBOOK_MAP["bad_deployment"] == "deployment_rollback"
        assert RUNBOOK_MAP["kubernetes_crashloop"] == "kubernetes_crashloop"


class TestRemediationRegistry:
    """Test the remediation action registry."""

    def test_default_actions_registered(self):
        """Test that all default actions are registered."""
        from app.remediation.registry import create_default_registry

        registry = create_default_registry()
        actions = registry.list_actions()

        action_types = [a.action_type for a in actions]
        assert "restart_service" in action_types
        assert "retry_health_check" in action_types
        assert "clear_cache" in action_types
        assert "k8s_rollout_restart" in action_types
        assert "rollback_deployment" in action_types
        assert "k8s_scale" in action_types

    def test_action_risk_levels(self):
        """Test that actions have appropriate risk levels."""
        from app.remediation.registry import create_default_registry

        registry = create_default_registry()

        # Low risk actions
        assert not registry.get("retry_health_check").approval_required
        assert not registry.get("clear_cache").approval_required
        assert not registry.get("refresh_monitoring").approval_required

        # Medium/High risk actions
        assert registry.get("restart_service").approval_required
        assert registry.get("k8s_rollout_restart").approval_required
        assert registry.get("rollback_deployment").approval_required

    def test_rollback_capability(self):
        """Test rollback capability flags."""
        from app.remediation.registry import create_default_registry

        registry = create_default_registry()

        assert registry.get("rollback_deployment").rollback_capable
        assert registry.get("k8s_rollout_restart").rollback_capable
        assert not registry.get("restart_service").rollback_capable


class TestSLOCalculator:
    """Test SLO/SLI calculations."""

    def test_severity_from_value(self):
        """Test severity calculation from metric values."""
        from app.domain.severity import severity_from_value, SeverityLevel

        assert severity_from_value(50.0, 85.0) == SeverityLevel.LOW
        assert severity_from_value(85.0, 85.0) == SeverityLevel.HIGH
        assert severity_from_value(97.75, 85.0) == SeverityLevel.CRITICAL

    def test_max_severity(self):
        """Test maximum severity calculation."""
        from app.domain.severity import max_severity, SeverityLevel

        assert max_severity("LOW", "HIGH") == SeverityLevel.HIGH
        assert max_severity("CRITICAL", "HIGH") == SeverityLevel.CRITICAL
        assert max_severity("MEDIUM", "MEDIUM") == SeverityLevel.MEDIUM


class TestServiceAPI:
    """Test service management API."""

    def test_create_and_list_service(self, auth_token):
        """Test creating and listing a service."""
        import uuid

        name = f"test-svc-{uuid.uuid4().hex[:8]}"

        # Create
        resp = client.post(
            "/api/v1/services",
            json={"name": name, "url": "http://localhost:8000/health"},
            headers=auth_token,
        )
        assert resp.status_code == 201
        service_id = resp.json()["id"]

        # List
        resp = client.get("/api/v1/services", headers=auth_token)
        assert resp.status_code == 200
        services = resp.json()
        assert any(s["id"] == service_id for s in services)

    def test_disable_enable_service(self, auth_token):
        """Test disabling and enabling a service."""
        import uuid

        name = f"test-svc-{uuid.uuid4().hex[:8]}"

        # Create
        resp = client.post(
            "/api/v1/services",
            json={"name": name, "url": "http://localhost:8000/health"},
            headers=auth_token,
        )
        service_id = resp.json()["id"]

        # Disable
        resp = client.post(
            f"/api/v1/services/{service_id}/disable",
            headers=auth_token,
        )
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is False

        # Enable
        resp = client.post(
            f"/api/v1/services/{service_id}/enable",
            headers=auth_token,
        )
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is True


class TestIncidentWorkflow:
    """Test the complete incident workflow."""

    def test_full_incident_lifecycle(self, auth_token):
        """Test the complete incident lifecycle via API."""
        # Create incident
        resp = client.post(
            "/api/v1/incidents",
            json={
                "title": "Integration Test Incident",
                "severity": "HIGH",
                "source": "integration_test",
            },
            headers=auth_token,
        )
        assert resp.status_code == 201
        incident_id = resp.json()["id"]
        assert resp.json()["status"] == "DETECTED"

        # Acknowledge
        resp = client.post(
            f"/api/v1/incidents/{incident_id}/acknowledge",
            headers=auth_token,
        )
        assert resp.status_code == 200
        assert resp.json()["acknowledged_at"] is not None

        # Request remediation
        resp = client.post(
            f"/api/v1/remediation/incidents/{incident_id}/actions",
            json={"action_type": "investigate"},
            headers=auth_token,
        )
        assert resp.status_code == 200
        action_id = resp.json()["id"]

        # Check if approval is needed
        resp = client.get(
            f"/api/v1/remediation/incidents/{incident_id}/actions",
            headers=auth_token,
        )
        action_status = resp.json()[0]["status"]

        if action_status == "PENDING":
            # Approve
            resp = client.post(
                f"/api/v1/remediation/actions/{action_id}/approve",
                json={"approved": True},
                headers=auth_token,
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "APPROVED"

        # Execute
        resp = client.post(
            f"/api/v1/remediation/actions/{action_id}/execute",
            headers=auth_token,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] in ["COMPLETED", "FAILED"]

        # Get timeline
        resp = client.get(
            f"/api/v1/incidents/{incident_id}/timeline",
            headers=auth_token,
        )
        assert resp.status_code == 200
        timeline = resp.json()
        assert len(timeline["events"]) > 0

        # Close incident
        resp = client.post(
            f"/api/v1/incidents/{incident_id}/close",
            headers=auth_token,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CLOSED"


class TestAuditLog:
    """Test audit logging."""

    def test_audit_log_entries(self, auth_token):
        """Test that actions are audit-logged."""
        # Perform an action
        client.post(
            "/api/v1/incidents",
            json={"title": "Audit Test", "severity": "LOW", "source": "audit_test"},
            headers=auth_token,
        )

        # Check audit log
        resp = client.get("/api/v1/audit?limit=10", headers=auth_token)
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) > 0
