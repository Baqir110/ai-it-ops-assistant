"""HTTP health monitor detector.

Periodically checks configured HTTP endpoints and emits detection
events for failures and latency degradation.
"""

import asyncio
import logging
import time

import httpx

from app.config.settings import settings
from app.database.models import Service
from app.database.repositories import (
    find_duplicate_detection,
    find_open_incident_for_service,
    get_recent_checks,
    get_service_availability,
    list_services,
    save_detection_event,
    save_service_check,
    update_service,
)
from app.detection.base import Detector, DetectionEvent
from app.domain.severity import SeverityLevel
from app.monitoring.metrics import (
    HTTP_CHECK_LATENCY,
    HTTP_CHECKS_TOTAL,
    HTTP_DETECTIONS,
)

logger = logging.getLogger(__name__)


class HTTPHealthDetector(Detector):
    """Monitors HTTP endpoints for availability and latency issues."""

    name = "http_health"

    def __init__(self, db_session_factory) -> None:
        self._db_factory = db_session_factory
        self._failure_counts: dict[str, int] = {}

    async def detect(self) -> list[DetectionEvent]:
        events: list[DetectionEvent] = []

        db = self._db_factory()
        try:
            services = list_services(db, include_disabled=False)

            async with httpx.AsyncClient(
                timeout=settings.HTTP_MONITOR_TIMEOUT_SECONDS,
                follow_redirects=True,
            ) as client:
                check_tasks = [self._check_service(client, db, svc) for svc in services]
                results = await asyncio.gather(*check_tasks, return_exceptions=True)

            for svc, result in zip(services, results):
                if isinstance(result, Exception):
                    continue

                check, is_new_failure, is_latency_issue = result

                if not check.available:
                    self._failure_counts[svc.name] = (
                        self._failure_counts.get(svc.name, 0) + 1
                    )
                else:
                    self._failure_counts[svc.name] = 0

                if is_new_failure or is_latency_issue:
                    events.append(
                        self._build_event(svc, check, is_new_failure, is_latency_issue)
                    )

        finally:
            db.close()

        return events

    async def _check_service(
        self, client: httpx.AsyncClient, db, service: Service
    ) -> tuple:
        """Check a single service and return (check, is_failure, is_latency_issue)."""
        if not service.url:
            # No URL — check if it's a TCP-style service
            return self._check_tcp(service, db), False, False

        start = time.monotonic()
        status_code = None
        error = None
        available = False

        try:
            response = await client.get(service.url)
            status_code = response.status_code
            latency_ms = (time.monotonic() - start) * 1000
            available = 200 <= status_code < 400
        except httpx.TimeoutException:
            latency_ms = (time.monotonic() - start) * 1000
            error = "Connection timeout"
        except httpx.ConnectError as e:
            latency_ms = (time.monotonic() - start) * 1000
            error = f"Connection error: {e}"
        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            error = str(e)

        HTTP_CHECKS_TOTAL.labels(
            service=service.name, result="success" if available else "failure"
        ).inc()
        HTTP_CHECK_LATENCY.labels(service=service.name).observe(latency_ms / 1000)

        check = save_service_check(
            db=db,
            service_id=service.id,
            status_code=status_code,
            latency_ms=round(latency_ms, 2),
            available=available,
            error=error,
        )

        # Update service health status
        update_service(
            db,
            service.id,
            health_status="healthy" if available else "unhealthy",
            last_health_check=check.checked_at,
        )

        failure_threshold = settings.HTTP_MONITOR_FAILURE_THRESHOLD
        is_failure = self._failure_counts.get(service.name, 0) >= failure_threshold
        is_latency = (
            latency_ms > settings.HTTP_MONITOR_LATENCY_THRESHOLD_MS and available
        )

        return check, is_failure, is_latency

    def _check_tcp(self, service: Service, db):
        """Fallback TCP check for services without HTTP URL."""
        import socket

        host_port = (service.metadata_ or {}).get("tcp_check")
        if not host_port:
            return None

        host, port_str = host_port.split(":")
        port = int(port_str)

        start = time.monotonic()
        try:
            sock = socket.create_connection((host, port), timeout=3.0)
            sock.close()
            latency_ms = (time.monotonic() - start) * 1000
            check = save_service_check(
                db=db,
                service_id=service.id,
                status_code=None,
                latency_ms=round(latency_ms, 2),
                available=True,
            )
        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            check = save_service_check(
                db=db,
                service_id=service.id,
                status_code=None,
                latency_ms=round(latency_ms, 2),
                available=False,
                error=str(e),
            )
            update_service(db, service.id, health_status="unhealthy")

        return check

    def _build_event(
        self, service: Service, check, is_failure: bool, is_latency: bool
    ) -> DetectionEvent:
        if is_failure:
            severity = SeverityLevel.HIGH.value
            event_type = "http_health_failure"
            message = (
                f"Service {service.name} failed health check "
                f"(status={check.status_code}, error={check.error})"
            )
            value = check.status_code or 0
            threshold = 200
        else:
            severity = SeverityLevel.MEDIUM.value
            event_type = "http_latency_degradation"
            message = (
                f"Service {service.name} latency degraded: "
                f"{check.latency_ms:.0f}ms (threshold: "
                f"{settings.HTTP_MONITOR_LATENCY_THRESHOLD_MS:.0f}ms)"
            )
            value = check.latency_ms
            threshold = settings.HTTP_MONITOR_LATENCY_THRESHOLD_MS

        HTTP_DETECTIONS.labels(type=event_type).inc()

        return DetectionEvent(
            source="http_monitor",
            type=event_type,
            severity=severity,
            message=message,
            service=service.name,
            value=value,
            threshold=threshold,
            environment=service.environment,
            metadata={
                "service_id": service.id,
                "latency_ms": check.latency_ms,
                "status_code": check.status_code,
                "consecutive_failures": self._failure_counts.get(service.name, 0),
            },
        )
