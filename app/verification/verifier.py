"""Automated recovery verification.

After remediation, verifies that the service has actually recovered
before marking an incident as RESOLVED.
"""

import logging
import time

import httpx

from app.config.settings import settings
from app.database.models import Incident, IncidentStatus
from app.database.repositories import (
    add_incident_event,
    get_incident,
    get_service,
    get_service_availability,
    update_incident,
    update_incident_status,
)
from app.monitoring.metrics import VERIFICATION_RUNS

logger = logging.getLogger(__name__)


class RecoveryVerifier:
    """Verifies service recovery after remediation."""

    def __init__(self, db_session_factory) -> None:
        self._db_factory = db_session_factory

    def verify(self, incident_id: int) -> bool:
        """Verify recovery for an incident. Returns True if recovered."""
        VERIFICATION_RUNS.inc()

        db = self._db_factory()
        try:
            incident = get_incident(db, incident_id)
            if not incident:
                return False

            if not incident.affected_service_id:
                # No service to verify — mark resolved
                update_incident_status(db, incident_id, IncidentStatus.RESOLVED.value)
                update_incident(
                    db,
                    incident_id,
                    remediation_status="verified",
                    remediation_result="No service to verify — resolved",
                )
                add_incident_event(
                    db,
                    incident_id=incident_id,
                    event_type="recovery_verified",
                    message="Incident resolved (no service to verify)",
                )
                return True

            service = get_service(db, incident.affected_service_id)
            if not service:
                return False

            # Run verification checks
            recovered = self._verify_service_recovery(service, incident)

            if recovered:
                update_incident_status(db, incident_id, IncidentStatus.RESOLVED.value)
                update_incident(
                    db,
                    incident_id,
                    remediation_status="verified",
                    remediation_result="Service recovered successfully",
                )
                add_incident_event(
                    db,
                    incident_id=incident_id,
                    event_type="recovery_verified",
                    message=f"Service {service.name} has recovered. Incident resolved.",
                )
            else:
                update_incident_status(db, incident_id, IncidentStatus.FAILED.value)
                update_incident(
                    db,
                    incident_id,
                    remediation_status="failed",
                    remediation_result="Service did not recover after remediation",
                )
                add_incident_event(
                    db,
                    incident_id=incident_id,
                    event_type="recovery_failed",
                    message=f"Service {service.name} did not recover after remediation.",
                )

            return recovered
        finally:
            db.close()

    def _verify_service_recovery(self, service, incident: Incident) -> bool:
        """Run recovery verification checks for a service."""
        checks_passed = 0

        for attempt in range(settings.VERIFICATION_MAX_ATTEMPTS):
            # Check 1: HTTP health
            if self._check_http_health(service):
                checks_passed += 1

            # Check 2: Availability over recent window
            db = self._db_factory()
            try:
                availability = get_service_availability(
                    db, service.id, window_minutes=5
                )
                if availability >= 95.0:
                    checks_passed += 1
            finally:
                db.close()

            # Check 3: Latency acceptable
            if self._check_latency(service):
                checks_passed += 1

            if checks_passed >= 2:
                return True

            if attempt < settings.VERIFICATION_MAX_ATTEMPTS - 1:
                time.sleep(settings.VERIFICATION_INTERVAL_SECONDS)
            checks_passed = 0

        return False

    def _check_http_health(self, service) -> bool:
        if not service.url:
            return True  # No URL to check

        try:
            resp = httpx.get(service.url, timeout=5.0)
            return 200 <= resp.status_code < 400
        except Exception:
            return False

    def _check_latency(self, service) -> bool:
        if not service.url:
            return True

        try:
            start = time.monotonic()
            httpx.get(service.url, timeout=5.0)
            latency_ms = (time.monotonic() - start) * 1000
            return latency_ms < settings.HTTP_MONITOR_LATENCY_THRESHOLD_MS
        except Exception:
            return False
