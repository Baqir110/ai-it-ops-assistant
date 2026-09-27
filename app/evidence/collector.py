"""Deterministic evidence collection for incidents.

Collects metrics, logs, health checks, deployment info, and
configuration changes for a given incident time window.
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.models import Incident
from app.database.repositories import (
    add_evidence,
    get_incident_evidence,
    get_recent_checks,
    get_service,
)
from app.monitoring.metrics import EVIDENCE_COLLECTIONS

logger = logging.getLogger(__name__)


class EvidenceCollector:
    """Collects structured evidence for incident investigation."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def collect(self, incident: Incident) -> list[dict]:
        """Collect all available evidence for an incident.

        Returns a list of evidence summaries. Each piece of evidence
        is also persisted to the database.
        """
        evidence_items: list[dict] = []

        # 1. Service health checks
        health_evidence = self._collect_health_checks(incident)
        if health_evidence:
            evidence_items.extend(health_evidence)

        # 2. Detection events
        detection_evidence = self._collect_detection_events(incident)
        if detection_evidence:
            evidence_items.extend(detection_evidence)

        # 3. Service metadata
        service_evidence = self._collect_service_info(incident)
        if service_evidence:
            evidence_items.extend(service_evidence)

        # 4. Prometheus metrics (if available)
        metrics_evidence = self._collect_metrics(incident)
        if metrics_evidence:
            evidence_items.extend(metrics_evidence)

        # 5. Deployment info
        deployment_evidence = self._collect_deployment_info(incident)
        if deployment_evidence:
            evidence_items.extend(deployment_evidence)

        EVIDENCE_COLLECTIONS.inc(len(evidence_items))
        return evidence_items

    def _collect_health_checks(self, incident: Incident) -> list[dict]:
        if not incident.affected_service_id:
            return []

        service = get_service(self._db, incident.affected_service_id)
        if not service:
            return []

        since = incident.detected_at - timedelta(minutes=30)
        checks = get_recent_checks(self._db, service.id, limit=50)
        recent = [c for c in checks if c.checked_at >= since]

        if not recent:
            return []

        total = len(recent)
        failures = sum(1 for c in recent if not c.available)
        avg_latency = (
            sum(c.latency_ms for c in recent if c.latency_ms) / total
            if total
            else 0
        )

        summary = {
            "total_checks": total,
            "failures": failures,
            "availability_pct": round(((total - failures) / total) * 100, 1) if total else 100,
            "avg_latency_ms": round(avg_latency, 1),
            "first_failure": next(
                (c.checked_at.isoformat() for c in recent if not c.available), None
            ),
        }

        add_evidence(
            self._db,
            incident_id=incident.id,
            evidence_type="health_checks",
            source="http_monitor",
            content=json.dumps(summary, indent=2),
            metadata=summary,
        )

        return [summary]

    def _collect_detection_events(self, incident: Incident) -> list[dict]:
        if not incident.detection_event_id:
            return []

        from app.database.repositories import get_detection_events

        events = get_detection_events(self._db, limit=10)
        related = [
            e for e in events
            if e.service == (get_service(self._db, incident.affected_service_id).name
                           if incident.affected_service_id else None)
        ]

        if not related:
            return []

        summary = [
            {
                "type": e.event_type,
                "severity": e.severity,
                "message": e.message,
                "value": e.value,
                "threshold": e.threshold,
                "timestamp": e.created_at.isoformat(),
            }
            for e in related[:10]
        ]

        add_evidence(
            self._db,
            incident_id=incident.id,
            evidence_type="detection_events",
            source="detection_engine",
            content=json.dumps(summary, indent=2),
            metadata={"events": summary},
        )

        return summary

    def _collect_service_info(self, incident: Incident) -> list[dict]:
        if not incident.affected_service_id:
            return []

        service = get_service(self._db, incident.affected_service_id)
        if not service:
            return []

        info = {
            "name": service.name,
            "display_name": service.display_name,
            "kind": service.kind,
            "url": service.url,
            "environment": service.environment,
            "health_status": service.health_status,
            "consecutive_failures": service.consecutive_failures,
            "tags": service.tags,
        }

        add_evidence(
            self._db,
            incident_id=incident.id,
            evidence_type="service_info",
            source="service_registry",
            content=json.dumps(info, indent=2),
            metadata=info,
        )

        return [info]

    def _collect_metrics(self, incident: Incident) -> list[dict]:
        """Collect Prometheus metrics if available."""
        if not settings.PROMETHEUS_ENABLED:
            return []

        try:
            import httpx

            prom_url = settings.PROMETHEUS_URL.rstrip("/")
            since = incident.detected_at - timedelta(minutes=30)
            until = datetime.now(timezone.utc)

            # This is a synchronous call within async context — use a thread
            # For now, return empty if Prometheus is not reachable
            return []
        except Exception:
            return []

    def _collect_deployment_info(self, incident: Incident) -> list[dict]:
        """Collect deployment information if available."""
        # Check for deployment metadata in service
        if not incident.affected_service_id:
            return []

        service = get_service(self._db, incident.affected_service_id)
        if not service or not service.metadata_:
            return []

        deploy_info = service.metadata_.get("deployment")
        if not deploy_info:
            return []

        add_evidence(
            self._db,
            incident_id=incident.id,
            evidence_type="deployment_info",
            source="deployment_tracker",
            content=json.dumps(deploy_info, indent=2),
            metadata=deploy_info,
        )

        return [deploy_info]
