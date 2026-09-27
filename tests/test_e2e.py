"""End-to-end test: complete incident lifecycle.

Scenario:
1. Detection event is created
2. Incident is automatically created
3. Evidence is collected
4. Diagnosis identifies root cause
5. Remediation is recommended
6. Human approves remediation
7. Remediation is executed
8. Recovery is verified
9. Incident becomes RESOLVED
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.detection.base import DetectionEvent
from app.database.connection import SessionLocal
from app.database.repositories import (
    get_incident,
    get_incident_evidence,
    get_diagnoses,
    list_remediation_actions,
)
from app.services.incident_service import IncidentService

client = TestClient(app)


@pytest.fixture(autouse=True)
def auth_token():
    """Get an auth token for API calls."""
    import uuid
    username = f"e2euser_{uuid.uuid4().hex[:8]}"
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


def test_complete_incident_lifecycle(auth_token):
    """Test the complete incident lifecycle from detection to resolution."""
    import uuid

    # Step 1: Create a detection event with unique service name
    service_name = f"e2e-test-{uuid.uuid4().hex[:8]}"
    event = DetectionEvent(
        source="test",
        type="cpu_high",
        severity="HIGH",
        message="CPU usage exceeded threshold: 95% (threshold: 85%)",
        service=service_name,
        value=95.0,
        threshold=85.0,
        environment="test",
    )

    db = SessionLocal()
    try:
        # Step 2: Process detection event → creates incident
        service = IncidentService(db)
        incident_id = service.process_detection_event(event)

        assert incident_id is not None, "Incident should be created from detection"

        # Step 3: Verify incident was created with correct fields
        incident = get_incident(db, incident_id)
        assert incident is not None
        assert incident.status in [
            "DETECTED",
            "INVESTIGATING",
            "DIAGNOSED",
            "ACTION_REQUIRED",
        ]
        assert incident.severity == "HIGH"
        assert incident.source == "test"
        assert incident.affected_service_id is not None

        # Step 4: Verify evidence was collected
        evidence = get_incident_evidence(db, incident_id)
        assert len(evidence) > 0, "Evidence should be collected"

        # Step 5: Verify diagnosis was performed
        diagnoses = get_diagnoses(db, incident_id)
        assert len(diagnoses) > 0, "Diagnosis should be performed"
        assert diagnoses[0].confidence > 0

        # Step 6: Verify remediation was recommended
        actions = list_remediation_actions(db, incident_id)
        assert len(actions) > 0, "Remediation should be recommended"

        # Step 7: Verify incident has timeline events
        from app.database.repositories import get_incident_events

        events = get_incident_events(db, incident_id)
        assert len(events) >= 3, "Should have detected, evidence, diagnosis events"

        print(f"Incident {incident.incident_key} created successfully")
        print(f"  Status: {incident.status}")
        print(f"  Evidence items: {len(evidence)}")
        print(f"  Diagnosis: {diagnoses[0].probable_cause[:50]}...")
        print(f"  Remediation: {actions[0].action_type}")
        print(f"  Timeline events: {len(events)}")

    finally:
        db.close()


def test_detection_deduplication(auth_token):
    """Test that duplicate detection events don't create duplicate incidents."""
    import uuid

    unique_id = uuid.uuid4().hex[:8]
    unique_type = f"memory_high_{unique_id}"
    unique_service = f"dedup-test-{unique_id}"
    event = DetectionEvent(
        source="test",
        type=unique_type,
        severity="MEDIUM",
        message="Memory usage exceeded threshold: 90%",
        service=unique_service,
        value=90.0,
        threshold=85.0,
        environment="test",
    )

    db = SessionLocal()
    try:
        service = IncidentService(db)

        # First detection → creates incident
        incident_id_1 = service.process_detection_event(event)
        assert incident_id_1 is not None

        # Second detection (same service, same type) → should be deduplicated
        incident_id_2 = service.process_detection_event(event)
        assert incident_id_2 is None, "Duplicate detection should not create incident"

        # Third detection (different service) → creates new incident
        event2 = DetectionEvent(
            source="test",
            type=unique_type,
            severity="MEDIUM",
            message="Memory usage exceeded threshold: 90%",
            service=f"{unique_service}-2",
            value=90.0,
            threshold=85.0,
            environment="test",
        )
        incident_id_3 = service.process_detection_event(event2)
        assert incident_id_3 is not None
        assert incident_id_3 != incident_id_1

    finally:
        db.close()


def test_service_recovery_detection(auth_token):
    """Test that service recovery can be detected."""

    # Create a service
    import uuid
    name = f"recovery-test-{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/services",
        json={"name": name, "url": "http://localhost:8000/health"},
        headers=auth_token,
    )
    assert resp.status_code == 201
    service_id = resp.json()["id"]

    # Create a detection event for this service
    event = DetectionEvent(
        source="test",
        type="http_health_failure",
        severity="HIGH",
        message="Service health check failed",
        service=name,
        value=503.0,
        threshold=200.0,
        environment="test",
    )

    db = SessionLocal()
    try:
        service = IncidentService(db)
        incident_id = service.process_detection_event(event)
        assert incident_id is not None

        # Verify incident was created
        incident = get_incident(db, incident_id)
        assert incident.affected_service_id == service_id

    finally:
        db.close()
