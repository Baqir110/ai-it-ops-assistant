"""Deterministic diagnosis engine.

Analyzes collected evidence to determine probable root causes.
Works without any AI provider — uses structured rules based on
evidence patterns. AI enhancement can be layered on top.
"""

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.database.models import Incident
from app.database.repositories import (
    get_diagnoses,
    get_incident_evidence,
    get_runbook_by_key,
    save_diagnosis,
)
from app.monitoring.metrics import DIAGNOSES_CREATED

logger = logging.getLogger(__name__)


@dataclass
class DiagnosisResult:
    probable_cause: str
    confidence: float
    alternative_causes: list[str] = field(default_factory=list)
    evidence_summary: str = ""
    recommended_action: str = ""
    runbook_key: str | None = None


# ── Runbook mapping ────────────────────────────────────────────────────

RUNBOOK_MAP = {
    "http_health_failure": "service_outage",
    "http_latency_degradation": "high_latency",
    "cpu_high": "cpu_high",
    "memory_high": "memory_pressure",
    "disk_high": "disk_pressure",
    "http_error_rate": "http_error_rate",
    "http_latency_p95": "high_latency",
    "kubernetes_crashloop": "kubernetes_crashloop",
    "bad_deployment": "deployment_rollback",
    "certificate_expiring": "certificate_expiry",
    "backup_failure": "backup_failure",
    "container_crash": "container_crash",
}


class DiagnosisEngine:
    """Deterministic diagnosis based on collected evidence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def diagnose(self, incident: Incident) -> DiagnosisResult:
        """Run diagnosis for an incident based on its evidence."""
        evidence = get_incident_evidence(self._db, incident.id)
        evidence_by_type: dict[str, list] = {}
        for e in evidence:
            evidence_by_type.setdefault(e.evidence_type, []).append(e)

        # Determine the incident classification from source/detection type
        event_type = incident.source or "unknown"
        runbook_key = RUNBOOK_MAP.get(event_type)

        # Analyze evidence patterns
        health_evidence = self._analyze_health_evidence(
            evidence_by_type.get("health_checks", [])
        )
        detection_evidence = self._analyze_detection_evidence(
            evidence_by_type.get("detection_events", [])
        )
        service_evidence = self._analyze_service_evidence(
            evidence_by_type.get("service_info", [])
        )

        # Build diagnosis based on evidence
        probable_cause, confidence, alternatives = self._determine_cause(
            incident, event_type, health_evidence, detection_evidence, service_evidence
        )

        recommended_action = self._recommend_action(event_type, probable_cause)

        result = DiagnosisResult(
            probable_cause=probable_cause,
            confidence=confidence,
            alternative_causes=alternatives,
            evidence_summary=self._build_evidence_summary(evidence),
            recommended_action=recommended_action,
            runbook_key=runbook_key,
        )

        # Persist diagnosis
        save_diagnosis(
            self._db,
            incident_id=incident.id,
            probable_cause=result.probable_cause,
            confidence=result.confidence,
            alternative_causes=result.alternative_causes,
            evidence_summary=result.evidence_summary,
            recommended_action=result.recommended_action,
            runbook_key=result.runbook_key,
        )

        DIAGNOSES_CREATED.inc()

        # AI enhancement (if configured)
        try:
            from app.services.ai_diagnosis import AIDiagnosisService

            ai_service = AIDiagnosisService()
            if ai_service.is_available():
                ai_result = ai_service.enhance_diagnosis(incident)
                if ai_result:
                    # Save AI-enhanced diagnosis as additional diagnosis
                    save_diagnosis(
                        self._db,
                        incident_id=incident.id,
                        probable_cause=ai_result.get("probable_cause", ""),
                        confidence=ai_result.get("confidence", 0),
                        alternative_causes=ai_result.get("alternative_causes", []),
                        evidence_summary=ai_result.get("reasoning", ""),
                        recommended_action=ai_result.get("recommended_action", ""),
                        runbook_key=result.runbook_key,
                    )
                    logger.info(
                        "AI-enhanced diagnosis saved for incident %s",
                        incident.incident_key,
                    )
        except Exception as e:
            logger.debug("AI enhancement skipped: %s", e)

        return result

    def _analyze_health_evidence(self, evidence: list) -> dict:
        if not evidence:
            return {}
        try:
            data = json.loads(evidence[0].content)
            return data
        except (json.JSONDecodeError, IndexError):
            return {}

    def _analyze_detection_evidence(self, evidence: list) -> dict:
        if not evidence:
            return {}
        try:
            data = json.loads(evidence[0].content)
            if isinstance(data, list) and data:
                return data[0]
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IndexError):
            return {}

    def _analyze_service_evidence(self, evidence: list) -> dict:
        if not evidence:
            return {}
        try:
            data = json.loads(evidence[0].content)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IndexError):
            return {}

    def _determine_cause(
        self,
        incident: Incident,
        event_type: str,
        health: dict,
        detection: dict,
        service: dict,
    ) -> tuple[str, float, list[str]]:
        """Determine probable root cause from evidence patterns."""

        if event_type == "http_health_failure":
            failures = health.get("failures", 0)
            availability = health.get("availability_pct", 100)
            if availability == 0:
                return (
                    f"Service {incident.affected_service_id} is completely unavailable. "
                    f"All health checks failing ({failures} consecutive failures).",
                    0.85,
                    [
                        "Service process crashed",
                        "Network connectivity issue",
                        "Dependency failure",
                    ],
                )
            return (
                f"Service experiencing intermittent failures. "
                f"Availability dropped to {availability}%.",
                0.70,
                [
                    "Resource exhaustion",
                    "Dependency degradation",
                    "Configuration issue",
                ],
            )

        if event_type == "http_latency_degradation":
            avg_latency = health.get("avg_latency_ms", 0)
            return (
                f"Service latency degraded to {avg_latency}ms average. "
                "Possible causes: resource contention, downstream dependency slowdown, or inefficient queries.",
                0.65,
                [
                    "Database slowdown",
                    "External API degradation",
                    "Resource contention",
                ],
            )

        if event_type == "cpu_high":
            return (
                "CPU utilization exceeded threshold. "
                "Possible causes: runaway process, insufficient capacity, or traffic spike.",
                0.70,
                ["Runaway process", "Traffic spike", "Insufficient CPU allocation"],
            )

        if event_type == "memory_high":
            return (
                "Memory utilization exceeded threshold. "
                "Possible causes: memory leak, insufficient memory, or cache buildup.",
                0.70,
                ["Memory leak", "Insufficient memory allocation", "Cache not evicting"],
            )

        if event_type == "disk_high":
            return (
                "Disk utilization exceeded threshold. "
                "Possible causes: log accumulation, large temp files, or insufficient disk space.",
                0.75,
                [
                    "Log files not rotated",
                    "Temporary files accumulating",
                    "Disk undersized",
                ],
            )

        if event_type == "http_error_rate":
            return (
                "HTTP error rate exceeded threshold. "
                "Possible causes: bad deployment, downstream service failure, or configuration error.",
                0.75,
                [
                    "Bad deployment",
                    "Downstream dependency failure",
                    "Configuration regression",
                ],
            )

        if event_type == "bad_deployment":
            return (
                "Deployment regression detected. Error rate spike correlates with recent deployment.",
                0.85,
                [
                    "Code regression",
                    "Configuration change",
                    "Dependency version mismatch",
                ],
            )

        if event_type == "kubernetes_crashloop":
            return (
                "Kubernetes pod in CrashLoopBackOff. "
                "Possible causes: application error on startup, missing config, or resource limits.",
                0.80,
                [
                    "Application startup failure",
                    "Missing ConfigMap/Secret",
                    "OOMKilled",
                ],
            )

        if event_type == "certificate_expiring":
            return (
                "SSL certificate expiring soon. "
                "Certificate renewal required to prevent service outage.",
                0.95,
                ["Certificate auto-renewal failed", "Manual renewal required"],
            )

        if event_type == "backup_failure":
            return (
                "Backup job failed. "
                "Possible causes: storage full, network issue, or backup script error.",
                0.80,
                [
                    "Storage capacity exceeded",
                    "Network connectivity",
                    "Backup script error",
                ],
            )

        # Generic fallback
        return (
            f"Operational anomaly detected: {incident.title}. "
            f"Source: {incident.source or 'unknown'}. "
            "Further investigation required.",
            0.40,
            ["Unknown — manual investigation needed"],
        )

    def _recommend_action(self, event_type: str, cause: str) -> str:
        """Recommend a remediation action based on the diagnosis."""
        action_map = {
            "http_health_failure": "restart_service",
            "http_latency_degradation": "scale_up",
            "cpu_high": "restart_service",
            "memory_high": "restart_service",
            "disk_high": "clear_logs",
            "http_error_rate": "rollback_deployment",
            "bad_deployment": "rollback_deployment",
            "kubernetes_crashloop": "k8s_rollout_restart",
            "certificate_expiring": "renew_certificate",
            "backup_failure": "retry_backup",
            "container_crash": "restart_container",
        }
        return action_map.get(event_type, "investigate")

    def _build_evidence_summary(self, evidence: list) -> str:
        if not evidence:
            return "No evidence collected."
        parts = []
        for e in evidence:
            parts.append(f"[{e.evidence_type}] {e.source}: {e.content[:200]}")
        return "\n\n".join(parts)
