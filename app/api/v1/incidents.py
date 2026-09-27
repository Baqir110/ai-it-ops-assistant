"""Incident API endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database.connection import get_db
from app.database.models import IncidentStatus, SeverityLevel
from app.database.repositories import (
    add_incident_event,
    create_incident,
    get_incident,
    get_incident_by_key,
    get_incident_evidence,
    get_incident_events,
    get_diagnoses,
    list_incidents,
    list_remediation_actions,
    update_incident,
    update_incident_status,
    save_audit_log,
)
from app.domain.incidents import can_transition, is_open, transition
from app.monitoring.metrics import INCIDENT_STATUS_CHANGES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incidents", tags=["Incidents"])


# ── Schemas ────────────────────────────────────────────────────────────


class IncidentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    severity: SeverityLevel = SeverityLevel.MEDIUM
    source: str | None = None
    affected_service_id: int | None = None
    environment: str = "production"
    symptoms: str | None = None


class IncidentUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: SeverityLevel | None = None
    symptoms: str | None = None


class StatusUpdateRequest(BaseModel):
    status: IncidentStatus


class IncidentResponse(BaseModel):
    id: int
    incident_key: str
    title: str
    description: str | None
    severity: str
    status: str
    source: str | None
    affected_service_id: int | None
    environment: str
    detected_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    duration: float | None
    symptoms: str | None
    probable_root_cause: str | None
    confidence: float | None
    recommended_remediation: str | None
    remediation_status: str | None
    remediation_result: str | None

    class Config:
        from_attributes = True


# ── Endpoints ──────────────────────────────────────────────────────────


@router.get("", response_model=list[IncidentResponse])
def list_all_incidents(
    status: str | None = None,
    severity: str | None = None,
    service_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List incidents with optional filtering."""
    incidents = list_incidents(
        db, status=status, severity=severity, service_id=service_id, limit=limit
    )
    return incidents


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_new_incident(
    request: IncidentCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Create a new incident manually."""
    incident = create_incident(
        db,
        title=request.title,
        severity=request.severity.value,
        source=request.source or "manual",
        affected_service_id=request.affected_service_id,
        environment=request.environment,
        description=request.description,
        symptoms=request.symptoms,
    )

    add_incident_event(
        db,
        incident_id=incident.id,
        event_type="created",
        message=f"Incident created by {current_user['username']}",
    )

    save_audit_log(
        db,
        action="incident_created",
        details={"incident_id": incident.id, "title": request.title},
        performed_by=current_user["username"],
        incident_id=incident.id,
    )

    return incident


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident_detail(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get detailed information about a specific incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("/{incident_id}/timeline")
def get_incident_timeline(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the full timeline of events for an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    events = get_incident_events(db, incident_id)
    evidence = get_incident_evidence(db, incident_id)
    diagnoses = get_diagnoses(db, incident_id)
    actions = list_remediation_actions(db, incident_id)

    return {
        "incident": incident,
        "events": events,
        "evidence": evidence,
        "diagnoses": diagnoses,
        "remediation_actions": actions,
    }


@router.patch("/{incident_id}", response_model=IncidentResponse)
def update_incident_details(
    incident_id: int,
    request: IncidentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Update incident details."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    update_data = request.model_dump(exclude_unset=True)
    if "severity" in update_data:
        update_data["severity"] = update_data["severity"].value

    updated = update_incident(db, incident_id, **update_data)

    add_incident_event(
        db,
        incident_id=incident_id,
        event_type="updated",
        message=f"Incident updated by {current_user['username']}",
    )

    return updated


@router.post("/{incident_id}/status", response_model=IncidentResponse)
def change_incident_status(
    incident_id: int,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Change incident status with state machine validation."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status = incident.status
    new_status = request.status.value

    if not can_transition(old_status, new_status):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {old_status} → {new_status}",
        )

    updated = update_incident_status(db, incident_id, new_status)

    INCIDENT_STATUS_CHANGES.labels(from_status=old_status, to_status=new_status).inc()

    add_incident_event(
        db,
        incident_id=incident_id,
        event_type="status_change",
        message=f"Status changed from {old_status} to {new_status} by {current_user['username']}",
    )

    save_audit_log(
        db,
        action="incident_status_change",
        details={"from": old_status, "to": new_status},
        performed_by=current_user["username"],
        incident_id=incident_id,
    )

    return updated


@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
def acknowledge_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Acknowledge an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    from datetime import datetime, timezone

    updated = update_incident(
        db, incident_id, acknowledged_at=datetime.now(timezone.utc)
    )

    add_incident_event(
        db,
        incident_id=incident_id,
        event_type="acknowledged",
        message=f"Incident acknowledged by {current_user['username']}",
    )

    save_audit_log(
        db,
        action="incident_acknowledged",
        performed_by=current_user["username"],
        incident_id=incident_id,
    )

    return updated


@router.post("/{incident_id}/investigate", response_model=IncidentResponse)
def investigate_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Trigger investigation: evidence collection, diagnosis, and remediation recommendation."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    from app.services.incident_service import IncidentService

    service = IncidentService(db)
    service._start_investigation(incident_id)

    # Refresh incident to get updated status
    db.refresh(incident)

    save_audit_log(
        db,
        action="incident_investigation_triggered",
        performed_by=current_user["username"],
        incident_id=incident_id,
    )

    return incident


@router.post("/{incident_id}/close", response_model=IncidentResponse)
def close_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Close an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if not can_transition(incident.status, IncidentStatus.CLOSED.value):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close incident from status {incident.status}",
        )

    updated = update_incident_status(db, incident_id, IncidentStatus.CLOSED.value)

    add_incident_event(
        db,
        incident_id=incident_id,
        event_type="closed",
        message=f"Incident closed by {current_user['username']}",
    )

    save_audit_log(
        db,
        action="incident_closed",
        performed_by=current_user["username"],
        incident_id=incident_id,
    )

    return updated
