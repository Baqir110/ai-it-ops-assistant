"""Incident service — orchestrates the complete incident lifecycle.

This is the central orchestrator that connects detection, evidence collection,
diagnosis, remediation, and recovery verification into an automated workflow.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.models import IncidentStatus, SeverityLevel
from app.database.repositories import (
    add_incident_event,
    add_evidence,
    create_incident,
    create_remediation_action,
    find_duplicate_detection,
    find_open_incident_for_service,
    get_incident,
    get_service,
    get_service_by_name,
    list_remediation_actions,
    save_audit_log,
    save_detection_event,
    update_incident,
    update_incident_status,
)
from app.detection.base import DetectionEvent
from app.diagnosis.engine import DiagnosisEngine
from app.evidence.collector import EvidenceCollector
from app.monitoring.metrics import (
    INCIDENTS_CREATED,
    INCIDENT_STATUS_CHANGES,
)
from app.verification.verifier import RecoveryVerifier

logger = logging.getLogger(__name__)


class IncidentService:
    """Orchestrates the complete incident lifecycle.

    Workflow:
    1. Detection event → Create incident
    2. Incident created → Collect evidence
    3. Evidence collected → Diagnose
    4. Diagnosis complete → Recommend remediation
    5. Remediation approved → Execute
    6. Remediation executed → Verify recovery
    7. Recovery verified → Resolve incident
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def process_detection_event(self, event: DetectionEvent) -> int | None:
        """Process a detection event and create an incident if needed.

        Returns the incident ID if created, None if duplicate or no action needed.
        """
        # Check for duplicate detection (same service + same type within window)
        existing = find_duplicate_detection(
            self._db,
            event_type=event.type,
            service=event.service,
            window_minutes=settings.INCIDENT_DEDUP_WINDOW_MINUTES,
        )
        if existing:
            logger.info("Duplicate detection skipped: %s", event.message)
            return None

        # Check for open incident on the same service
        service_id = None
        if event.service:
            service = get_service_by_name(self._db, event.service)
            if service:
                service_id = service.id
                open_incident = find_open_incident_for_service(
                    self._db, service_id, event_type=event.type
                )
                if open_incident:
                    logger.info(
                        "Open incident already exists for %s: %s",
                        event.service,
                        open_incident.incident_key,
                    )
                    return None
            else:
                # Auto-register the service if it doesn't exist
                from app.database.repositories import create_service

                service = create_service(
                    self._db,
                    name=event.service,
                    url=None,
                    environment=event.environment,
                )
                service_id = service.id

        # Save detection event
        detection_event = save_detection_event(
            self._db,
            source=event.source,
            event_type=event.type,
            severity=event.severity,
            message=event.message,
            service=event.service,
            value=event.value,
            threshold=event.threshold,
            environment=event.environment,
        )

        # Create incident
        incident = create_incident(
            self._db,
            title=self._build_incident_title(event),
            severity=event.severity,
            source=event.source,
            affected_service_id=service_id,
            environment=event.environment,
            description=event.message,
            symptoms=event.message,
            detection_event_id=detection_event.id,
        )

        # Link detection event to incident
        detection_event.incident_id = incident.id
        self._db.commit()

        INCIDENTS_CREATED.labels(severity=event.severity).inc()

        add_incident_event(
            self._db,
            incident_id=incident.id,
            event_type="detected",
            message=f"Incident detected: {event.message}",
            metadata=event.metadata,
        )

        save_audit_log(
            self._db,
            action="incident_created",
            details={
                "incident_id": incident.id,
                "detection_event_id": detection_event.id,
                "source": event.source,
            },
            performed_by="system",
            incident_id=incident.id,
        )

        logger.info(
            "Incident %s created from detection: %s",
            incident.incident_key,
            event.message,
        )

        # Automatically start investigation
        self._start_investigation(incident.id)

        return incident.id

    def _start_investigation(self, incident_id: int) -> None:
        """Start investigation: collect evidence and diagnose."""
        incident = get_incident(self._db, incident_id)
        if not incident:
            return

        # Transition to INVESTIGATING
        if incident.status == IncidentStatus.DETECTED.value:
            update_incident_status(
                self._db, incident_id, IncidentStatus.INVESTIGATING.value
            )
            INCIDENT_STATUS_CHANGES.labels(
                from_status=IncidentStatus.DETECTED.value,
                to_status=IncidentStatus.INVESTIGATING.value,
            ).inc()

            add_incident_event(
                self._db,
                incident_id=incident_id,
                event_type="investigation_started",
                message="Investigation started",
            )

        # Collect evidence
        self._collect_evidence(incident_id)

        # Diagnose
        self._diagnose(incident_id)

    def _collect_evidence(self, incident_id: int) -> None:
        """Collect evidence for an incident."""
        incident = get_incident(self._db, incident_id)
        if not incident:
            return

        collector = EvidenceCollector(self._db)
        evidence_items = collector.collect(incident)

        add_incident_event(
            self._db,
            incident_id=incident_id,
            event_type="evidence_collected",
            message=f"Collected {len(evidence_items)} evidence items",
        )

        logger.info(
            "Evidence collected for incident %s: %d items",
            incident.incident_key,
            len(evidence_items),
        )

    def _diagnose(self, incident_id: int) -> None:
        """Run diagnosis for an incident."""
        incident = get_incident(self._db, incident_id)
        if not incident:
            return

        engine = DiagnosisEngine(self._db)
        diagnosis = engine.diagnose(incident)

        # Update incident with diagnosis results
        update_incident(
            self._db,
            incident_id,
            probable_root_cause=diagnosis.probable_cause,
            confidence=diagnosis.confidence,
            recommended_remediation=diagnosis.recommended_action,
        )

        # Transition to DIAGNOSED
        if incident.status == IncidentStatus.INVESTIGATING.value:
            update_incident_status(
                self._db, incident_id, IncidentStatus.DIAGNOSED.value
            )
            INCIDENT_STATUS_CHANGES.labels(
                from_status=IncidentStatus.INVESTIGATING.value,
                to_status=IncidentStatus.DIAGNOSED.value,
            ).inc()

            add_incident_event(
                self._db,
                incident_id=incident_id,
                event_type="diagnosed",
                message=f"Diagnosis: {diagnosis.probable_cause}",
                metadata={
                    "confidence": diagnosis.confidence,
                    "recommended_action": diagnosis.recommended_action,
                },
            )

        # Create remediation recommendation
        if diagnosis.recommended_action:
            self._recommend_remediation(incident_id, diagnosis.recommended_action)

        logger.info(
            "Diagnosis complete for incident %s: %s (confidence: %.2f)",
            incident.incident_key,
            diagnosis.probable_cause,
            diagnosis.confidence,
        )

    def _recommend_remediation(self, incident_id: int, action_type: str) -> None:
        """Create a remediation recommendation."""
        from app.remediation.registry import create_default_registry

        registry = create_default_registry()
        action_def = registry.get(action_type)

        if not action_def:
            logger.warning("Unknown remediation action: %s", action_type)
            return

        action = create_remediation_action(
            self._db,
            incident_id=incident_id,
            action_type=action_type,
            risk_level=action_def["risk_level"].value,
            approval_required=action_def["approval_required"],
            requested_by="system",
            rollback_capable=action_def["rollback_capable"],
        )

        # Auto-approve low-risk actions if configured
        if not action_def["approval_required"] or (
            action_def["risk_level"].value == "LOW"
            and settings.REMEDIATION_AUTO_APPROVE_LOW_RISK
        ):
            from datetime import datetime, timezone

            from app.database.models import RemediationActionStatus

            action.status = RemediationActionStatus.APPROVED.value
            action.approved_by = "system"
            action.approved_at = datetime.now(timezone.utc)
            self._db.commit()

        # Transition to ACTION_REQUIRED
        incident = get_incident(self._db, incident_id)
        if incident and incident.status == IncidentStatus.DIAGNOSED.value:
            update_incident_status(
                self._db, incident_id, IncidentStatus.ACTION_REQUIRED.value
            )
            INCIDENT_STATUS_CHANGES.labels(
                from_status=IncidentStatus.DIAGNOSED.value,
                to_status=IncidentStatus.ACTION_REQUIRED.value,
            ).inc()

            add_incident_event(
                self._db,
                incident_id=incident_id,
                event_type="remediation_recommended",
                message=f"Remediation recommended: {action_type}",
                metadata={
                    "action_id": action.id,
                    "risk_level": action_def["risk_level"].value,
                },
            )

        logger.info(
            "Remediation recommended for incident %s: %s",
            incident.incident_key if incident else "unknown",
            action_type,
        )

    def execute_remediation(self, action_id: int, executed_by: str) -> bool:
        """Execute a remediation action and verify recovery."""
        from app.database.models import RemediationActionStatus
        from app.database.repositories import (
            get_remediation_action,
            save_remediation_execution,
            update_remediation_action,
        )
        from app.remediation.registry import create_default_registry

        action = get_remediation_action(self._db, action_id)
        if not action:
            raise ValueError(f"Remediation action {action_id} not found")

        if action.status != RemediationActionStatus.APPROVED.value:
            raise ValueError(f"Action must be APPROVED before execution")

        registry = create_default_registry()
        action_def = registry.get(action.action_type)
        if not action_def:
            raise ValueError(f"Unknown action type: {action.action_type}")

        # Mark as executing
        action.status = RemediationActionStatus.EXECUTING.value
        action.started_at = datetime.now(timezone.utc)
        self._db.commit()

        # Update incident status
        incident = get_incident(self._db, action.incident_id)
        if incident:
            update_incident_status(
                self._db, action.incident_id, IncidentStatus.REMEDIATING.value
            )

        # Execute
        try:
            result = action_def.executor({})
            success = result.get("success", False)
            output = result.get("output", "")

            action.status = (
                RemediationActionStatus.COMPLETED.value
                if success
                else RemediationActionStatus.FAILED.value
            )
            action.completed_at = datetime.now(timezone.utc)
            action.result = "success" if success else "failed"
            action.output = output
            self._db.commit()

            save_remediation_execution(
                self._db,
                action_id=action_id,
                result="success" if success else "failed",
                executed_by=executed_by,
                output=output,
            )

            add_incident_event(
                self._db,
                incident_id=action.incident_id,
                event_type="remediation_executed",
                message=f"Action {action.action_type} {'succeeded' if success else 'failed'}: {output[:200]}",
            )

            # Verify recovery
            if success:
                self._verify_recovery(action.incident_id)

            return success

        except Exception as e:
            action.status = RemediationActionStatus.FAILED.value
            action.completed_at = datetime.now(timezone.utc)
            action.result = "failed"
            action.output = str(e)
            self._db.commit()

            add_incident_event(
                self._db,
                incident_id=action.incident_id,
                event_type="remediation_failed",
                message=f"Action {action.action_type} failed: {str(e)}",
            )

            return False

    def _verify_recovery(self, incident_id: int) -> bool:
        """Verify recovery after remediation."""
        verifier = RecoveryVerifier(lambda: self._db)
        # Run synchronous verification
        recovered = verifier.verify(incident_id)

        if recovered:
            logger.info("Incident %s verified as recovered", incident_id)
        else:
            logger.warning("Incident %s recovery verification failed", incident_id)

        return recovered

    def _build_incident_title(self, event: DetectionEvent) -> str:
        """Build an incident title from a detection event."""
        service_part = f" [{event.service}]" if event.service else ""
        return f"{event.type.replace('_', ' ').title()}{service_part}"
