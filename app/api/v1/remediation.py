"""Remediation and approval API endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.config.settings import settings
from app.database.connection import get_db
from app.database.models import RemediationActionStatus, RemediationRisk
from app.database.repositories import (
    add_incident_event,
    create_remediation_action,
    get_incident,
    get_remediation_action,
    list_remediation_actions,
    save_audit_log,
    save_remediation_execution,
    update_incident_status,
    update_remediation_action,
)
from app.domain.incidents import can_transition
from app.monitoring.metrics import REMEDIATION_ACTIONS
from app.remediation.registry import RemediationRegistry, create_default_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/remediation", tags=["Remediation"])

_registry: RemediationRegistry | None = None


def get_registry() -> RemediationRegistry:
    global _registry
    if _registry is None:
        _registry = create_default_registry()
    return _registry


# ── Schemas ────────────────────────────────────────────────────────────


class RemediationRequest(BaseModel):
    action_type: str = Field(..., min_length=1)
    parameters: dict = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    approved: bool
    notes: str | None = None


class RemediationActionResponse(BaseModel):
    id: int
    incident_id: int
    action_type: str
    risk_level: str
    approval_required: bool
    status: str
    requested_by: str | None
    approved_by: str | None
    started_at: datetime | None
    completed_at: datetime | None
    result: str | None
    output: str | None
    rollback_capable: bool

    class Config:
        from_attributes = True


# ── Endpoints ──────────────────────────────────────────────────────────


@router.get("/actions")
def list_available_actions(
    current_user: dict = Depends(get_current_user),
):
    """List all available remediation actions."""
    registry = get_registry()
    actions = registry.list_actions()
    result = []
    for action_type in actions:
        a = registry.get(action_type)
        result.append(
            {
                "action_type": action_type,
                "risk_level": a["risk_level"].value,
                "approval_required": a["approval_required"],
                "rollback_capable": a["rollback_capable"],
                "description": a["description"],
            }
        )
    return result


@router.post(
    "/incidents/{incident_id}/actions", response_model=RemediationActionResponse
)
def request_remediation(
    incident_id: int,
    request: RemediationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Request a remediation action for an incident."""
    incident = get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    registry = get_registry()
    action_def = registry.get(request.action_type)
    if not action_def:
        raise HTTPException(
            status_code=400,
            detail=f"Action type '{request.action_type}' is not allowed",
        )

    # Create the action
    action = create_remediation_action(
        db,
        incident_id=incident_id,
        action_type=request.action_type,
        risk_level=action_def["risk_level"].value,
        approval_required=action_def["approval_required"],
        requested_by=current_user["username"],
        rollback_capable=action_def["rollback_capable"],
    )

    # Auto-approve low-risk actions if configured
    if not action_def["approval_required"] or (
        action_def["risk_level"] == RemediationRisk.LOW
        and settings.REMEDIATION_AUTO_APPROVE_LOW_RISK
    ):
        update_remediation_action(
            db,
            action.id,
            status=RemediationActionStatus.APPROVED.value,
            approved_by="system",
            approved_at=datetime.now(tz=__import__("datetime").timezone.utc),
        )

    # Update incident status
    if can_transition(incident.status, "ACTION_REQUIRED"):
        update_incident_status(db, incident_id, "ACTION_REQUIRED")

    add_incident_event(
        db,
        incident_id=incident_id,
        event_type="remediation_requested",
        message=f"Remediation requested: {request.action_type} by {current_user['username']}",
    )

    save_audit_log(
        db,
        action="remediation_requested",
        details={"action_type": request.action_type, "action_id": action.id},
        performed_by=current_user["username"],
        incident_id=incident_id,
    )

    return action


@router.post("/actions/{action_id}/approve", response_model=RemediationActionResponse)
def approve_remediation_action(
    action_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Approve or reject a remediation action."""
    action = get_remediation_action(db, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found")

    if action.status != RemediationActionStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Action is not in PENDING state (current: {action.status})",
        )

    if request.approved:
        update_remediation_action(
            db,
            action_id,
            status=RemediationActionStatus.APPROVED.value,
            approved_by=current_user["username"],
            approved_at=datetime.now(tz=__import__("datetime").timezone.utc),
        )

        add_incident_event(
            db,
            incident_id=action.incident_id,
            event_type="remediation_approved",
            message=f"Action {action.action_type} approved by {current_user['username']}",
        )
    else:
        update_remediation_action(
            db,
            action_id,
            status=RemediationActionStatus.REJECTED.value,
            approved_by=current_user["username"],
            approved_at=datetime.now(tz=__import__("datetime").timezone.utc),
        )

        add_incident_event(
            db,
            incident_id=action.incident_id,
            event_type="remediation_rejected",
            message=f"Action {action.action_type} rejected by {current_user['username']}",
        )

    save_audit_log(
        db,
        action="remediation_approved" if request.approved else "remediation_rejected",
        details={"action_id": action_id, "action_type": action.action_type},
        performed_by=current_user["username"],
        incident_id=action.incident_id,
    )

    return get_remediation_action(db, action_id)


@router.post("/actions/{action_id}/execute", response_model=RemediationActionResponse)
def execute_remediation_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Execute an approved remediation action."""
    action = get_remediation_action(db, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found")

    if action.status != RemediationActionStatus.APPROVED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Action must be APPROVED before execution (current: {action.status})",
        )

    registry = get_registry()
    action_def = registry.get(action.action_type)
    if not action_def:
        raise HTTPException(status_code=400, detail="Unknown action type")

    # Mark as executing
    update_remediation_action(
        db,
        action_id,
        status=RemediationActionStatus.EXECUTING.value,
        started_at=datetime.now(tz=__import__("datetime").timezone.utc),
    )

    # Update incident status
    incident = get_incident(db, action.incident_id)
    if incident and can_transition(incident.status, "REMEDIATING"):
        update_incident_status(db, action.incident_id, "REMEDIATING")

    # Execute the action
    try:
        result = action_def["executor"]({})
        success = result.get("success", False)
        output = result.get("output", "")

        action_status = (
            RemediationActionStatus.COMPLETED.value
            if success
            else RemediationActionStatus.FAILED.value
        )
        action_result = "success" if success else "failed"

        update_remediation_action(
            db,
            action_id,
            status=action_status,
            completed_at=datetime.now(tz=__import__("datetime").timezone.utc),
            result=action_result,
            output=output,
        )

        save_remediation_execution(
            db,
            action_id=action_id,
            result=action_result,
            executed_by=current_user["username"],
            output=output,
        )

        REMEDIATION_ACTIONS.labels(
            action_type=action.action_type, result=action_result
        ).inc()

        add_incident_event(
            db,
            incident_id=action.incident_id,
            event_type="remediation_executed",
            message=f"Action {action.action_type} {action_result}: {output[:200]}",
        )

        save_audit_log(
            db,
            action="remediation_executed",
            details={
                "action_id": action_id,
                "action_type": action.action_type,
                "result": action_result,
            },
            performed_by=current_user["username"],
            incident_id=action.incident_id,
        )

        # Trigger recovery verification
        if success:
            from app.verification.verifier import RecoveryVerifier

            verifier = RecoveryVerifier(lambda: db)
            verifier.verify(action.incident_id)

    except Exception as e:
        update_remediation_action(
            db,
            action_id,
            status=RemediationActionStatus.FAILED.value,
            completed_at=datetime.now(tz=__import__("datetime").timezone.utc),
            result="failed",
            output=str(e),
        )
        REMEDIATION_ACTIONS.labels(
            action_type=action.action_type, result="failed"
        ).inc()
        logger.exception("Remediation execution failed")

    return get_remediation_action(db, action_id)


@router.post("/actions/{action_id}/rollback", response_model=RemediationActionResponse)
def rollback_remediation_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Rollback a remediation action if supported."""
    action = get_remediation_action(db, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Remediation action not found")

    if not action.rollback_capable:
        raise HTTPException(status_code=400, detail="Action does not support rollback")

    if action.rollback_executed:
        raise HTTPException(
            status_code=400, detail="Action has already been rolled back"
        )

    update_remediation_action(
        db,
        action_id,
        rollback_executed=True,
        rollback_result="Rollback executed",
    )

    add_incident_event(
        db,
        incident_id=action.incident_id,
        event_type="remediation_rolled_back",
        message=f"Action {action.action_type} rolled back by {current_user['username']}",
    )

    save_audit_log(
        db,
        action="remediation_rolled_back",
        details={"action_id": action_id},
        performed_by=current_user["username"],
        incident_id=action.incident_id,
    )

    return get_remediation_action(db, action_id)


@router.get(
    "/incidents/{incident_id}/actions", response_model=list[RemediationActionResponse]
)
def get_incident_remediation_actions(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all remediation actions for an incident."""
    return list_remediation_actions(db, incident_id)
