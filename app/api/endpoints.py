"""Legacy telemetry endpoints (backward compatibility).

These endpoints are preserved for backward compatibility with the
original AI IT Operations Assistant API. New code should use the
v1 incident and detection APIs.
"""

import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.repositories import list_incidents
from app.monitoring.metrics import (
    ANOMALIES_DETECTED,
    CPU_USAGE,
    DISK_USAGE,
    INCIDENTS_CREATED,
    RAM_USAGE,
    REQUEST_LATENCY,
    TELEMETRY_REQUESTS,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class SystemTelemetry(BaseModel):
    """Legacy telemetry payload format."""
    cpu_percent: float = Field(..., ge=0.0, le=100.0)
    ram_percent: float = Field(..., ge=0.0, le=100.0)
    disk_percent: float = Field(..., ge=0.0, le=100.0)
    services: dict[str, str] = Field(default_factory=dict)
    http_endpoints: dict[str, int] = Field(default_factory=dict)


class IncidentReport(BaseModel):
    """Legacy incident report format."""
    incident_title: str
    severity: str
    likely_cause: str
    recommended_actions: list[str]
    escalation_required: bool
    escalation_criteria: str | None = None
    sources_consulted: list = Field(default_factory=list)
    analysis_method: str = "RULE_BASED"


@router.post(
    "/telemetry/analyze",
    response_model=IncidentReport,
    status_code=status.HTTP_200_OK,
    summary="Analyze system telemetry (legacy)",
    description="Legacy endpoint for backward compatibility. Use /api/v1/incidents for new integrations.",
)
def analyze_telemetry(
    telemetry: SystemTelemetry,
    db: Session = Depends(get_db),
) -> IncidentReport:
    """Analyze telemetry and return an incident report (legacy format)."""
    start_time = perf_counter()

    TELEMETRY_REQUESTS.inc()

    CPU_USAGE.set(telemetry.cpu_percent)
    RAM_USAGE.set(telemetry.ram_percent)
    DISK_USAGE.set(telemetry.disk_percent)

    try:
        from app.engine.anomaly_detector import AnomalyDetector

        detector = AnomalyDetector()
        detection = detector.evaluate(telemetry)

        anomaly_count = detection["anomaly_count"]

        if detection["has_anomalies"]:
            ANOMALIES_DETECTED.inc(anomaly_count)

        # Build legacy report
        if not detection["has_anomalies"]:
            report = IncidentReport(
                incident_title="System Health Normal",
                severity="LOW",
                likely_cause="All systems operating within normal parameters.",
                recommended_actions=["Continue routine monitoring."],
                escalation_required=False,
            )
        else:
            from app.database.models import SeverityLevel
            from app.domain.severity import severity_from_value

            max_value = max(telemetry.cpu_percent, telemetry.ram_percent, telemetry.disk_percent)
            severity = severity_from_value(max_value, 85.0)

            # Persist incident
            from app.database.repositories import create_incident, find_open_incident_for_service

            existing = find_open_incident_for_service(db, None, event_type="telemetry_anomaly")
            if not existing:
                create_incident(
                    db,
                    title=f"Incident: Infrastructure Degradation ({', '.join(detection['anomalies'][:2])})",
                    severity=severity.value,
                    source="telemetry",
                    environment="production",
                    description=f"Detected {anomaly_count} anomaly/anomalies: {'; '.join(detection['anomalies'])}.",
                    symptoms="; ".join(detection["anomalies"]),
                )

            report = IncidentReport(
                incident_title=f"Incident: Infrastructure Degradation ({', '.join(detection['anomalies'][:2])})",
                severity=severity.value,
                likely_cause=f"Detected {anomaly_count} anomaly/anomalies: {'; '.join(detection['anomalies'])}.",
                recommended_actions=[
                    "Inspect system and application logs for critical errors.",
                    "Verify process states and resource consumption.",
                ],
                escalation_required=severity in {SeverityLevel.HIGH, SeverityLevel.CRITICAL},
                escalation_criteria="Escalate if metrics do not improve after initial investigation.",
            )

        INCIDENTS_CREATED.labels(severity=report.severity).inc()

        return report

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process telemetry payload: {e}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process telemetry payload: {str(e)}",
        ) from e

    finally:
        REQUEST_LATENCY.observe(perf_counter() - start_time)


@router.get(
    "/incidents",
    status_code=status.HTTP_200_OK,
    summary="List recent incidents (legacy)",
)
def get_incidents(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    """List incidents (legacy format)."""
    incidents = list_incidents(db, limit=limit)

    return {
        "value": incidents,
        "count": len(incidents),
    }
