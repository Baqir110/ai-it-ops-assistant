from typing import Optional
import uuid
from app.models.telemetry import TelemetryPayload
from app.models.incident import IncidentReport


def evaluate_telemetry(payload: TelemetryPayload) -> Optional[IncidentReport]:
    """Evaluates telemetry data against operational threshold rules."""
    triggered = []

    # Rule 1: Threshold Violation
    if payload.metric_value > payload.threshold:
        triggered.append(
            f"{payload.metric_type} exceeded threshold ({payload.metric_value} > {payload.threshold})"
        )

    # Rule 2: Explicit critical status
    if payload.status.lower() in ["critical", "error", "fatal"]:
        triggered.append(f"Explicit status reported: {payload.status}")

    if not triggered:
        return None

    # Determine severity
    severity = (
        "CRITICAL" if payload.metric_value >= payload.threshold * 1.15 else "HIGH"
    )

    return IncidentReport(
        incident_id=f"INC-{uuid.uuid4().hex[:6].upper()}",
        service_name=payload.service_name,
        severity=severity,
        description=f"Rule trigger on {payload.service_name} for {payload.metric_type}.",
        triggered_rules=triggered,
        suggested_runbook=(
            "disk_and_webserver.md"
            if "cpu" in payload.metric_type or "disk" in payload.metric_type
            else "network_issues.md"
        ),
    )
