"""SLO/SLI calculation engine.

Computes availability, error rate, latency, MTTD, MTTR, and
other SRE metrics from collected data.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, and_, select
from sqlalchemy.orm import Session

from app.database.models import (
    Incident,
    IncidentStatus,
    Service,
    ServiceCheck,
    SLOMeasurement,
    SLODefinition,
)
from app.database.repositories import (
    get_slo_measurements,
    list_incidents,
    list_slo_definitions,
    save_slo_measurement,
)
from app.monitoring.metrics import SLO_MEASUREMENTS

logger = logging.getLogger(__name__)


class SLOCalculator:
    """Calculates SLO/SLI metrics from operational data."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def evaluate_all(self) -> list[dict]:
        """Evaluate all enabled SLO definitions."""
        results = []
        definitions = list_slo_definitions(self._db)

        for slo in definitions:
            try:
                result = self._evaluate_slo(slo)
                if result:
                    results.append(result)
                    SLO_MEASUREMENTS.labels(
                        slo=slo.name, within_target=str(result["within_target"])
                    ).inc()
            except Exception as e:
                logger.warning("SLO evaluation failed for %s: %s", slo.name, e)

        return results

    def _evaluate_slo(self, slo: SLODefinition) -> dict | None:
        """Evaluate a single SLO definition."""
        metric_name = slo.metric_name

        if metric_name == "availability":
            value = self._calculate_availability()
        elif metric_name == "error_rate":
            value = self._calculate_error_rate()
        elif metric_name == "latency_p95":
            value = self._calculate_latency_p95()
        elif metric_name == "mttd":
            value = self._calculate_mttd()
        elif metric_name == "mttr":
            value = self._calculate_mttr()
        elif metric_name == "incident_count":
            value = float(self._count_incidents())
        else:
            return None

        within_target = value <= slo.target_value

        save_slo_measurement(
            self._db,
            slo_id=slo.id,
            actual_value=round(value, 4),
            within_target=within_target,
        )

        return {
            "slo_name": slo.name,
            "metric_name": metric_name,
            "actual_value": round(value, 4),
            "target_value": slo.target_value,
            "within_target": within_target,
            "window": slo.window,
        }

    def _calculate_availability(self) -> float:
        """Calculate overall service availability percentage."""
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        total_checks = self._db.scalar(
            select(func.count(ServiceCheck.id)).where(ServiceCheck.checked_at >= since)
        )
        if not total_checks:
            return 100.0

        available_checks = self._db.scalar(
            select(func.count(ServiceCheck.id)).where(
                and_(ServiceCheck.checked_at >= since, ServiceCheck.available.is_(True))
            )
        )
        return (available_checks / total_checks) * 100.0

    def _calculate_error_rate(self) -> float:
        """Calculate HTTP error rate percentage."""
        since = datetime.now(timezone.utc) - timedelta(hours=1)

        total = self._db.scalar(
            select(func.count(ServiceCheck.id)).where(ServiceCheck.checked_at >= since)
        )
        if not total:
            return 0.0

        errors = self._db.scalar(
            select(func.count(ServiceCheck.id)).where(
                and_(
                    ServiceCheck.checked_at >= since,
                    ServiceCheck.status_code >= 400,
                )
            )
        )
        return (errors / total) * 100.0

    def _calculate_latency_p95(self) -> float:
        """Calculate p95 latency in milliseconds."""
        since = datetime.now(timezone.utc) - timedelta(hours=1)

        latencies = self._db.scalars(
            select(ServiceCheck.latency_ms)
            .where(
                and_(
                    ServiceCheck.checked_at >= since,
                    ServiceCheck.latency_ms.is_not(None),
                )
            )
            .order_by(ServiceCheck.latency_ms)
        ).all()

        if not latencies:
            return 0.0

        index = int(len(latencies) * 0.95)
        return latencies[min(index, len(latencies) - 1)]

    def _calculate_mttd(self) -> float:
        """Calculate Mean Time To Detect in minutes."""
        since = datetime.now(timezone.utc) - timedelta(days=30)

        incidents = self._db.scalars(
            select(Incident).where(
                and_(
                    Incident.detected_at >= since,
                    Incident.acknowledged_at.is_not(None),
                )
            )
        ).all()

        if not incidents:
            return 0.0

        total_minutes = sum(
            (inc.acknowledged_at - inc.detected_at).total_seconds() / 60
            for inc in incidents
            if inc.acknowledged_at
        )
        return total_minutes / len(incidents)

    def _calculate_mttr(self) -> float:
        """Calculate Mean Time To Resolve in minutes."""
        since = datetime.now(timezone.utc) - timedelta(days=30)

        incidents = self._db.scalars(
            select(Incident).where(
                and_(
                    Incident.detected_at >= since,
                    Incident.resolved_at.is_not(None),
                )
            )
        ).all()

        if not incidents:
            return 0.0

        total_minutes = sum(
            (inc.resolved_at - inc.detected_at).total_seconds() / 60
            for inc in incidents
            if inc.resolved_at
        )
        return total_minutes / len(incidents)

    def _count_incidents(self) -> int:
        """Count incidents in the last 30 days."""
        since = datetime.now(timezone.utc) - timedelta(days=30)
        return (
            self._db.scalar(
                select(func.count(Incident.id)).where(Incident.detected_at >= since)
            )
            or 0
        )

    def get_sre_summary(self) -> dict:
        """Get a summary of key SRE metrics."""
        return {
            "availability_24h": round(self._calculate_availability(), 2),
            "error_rate_1h": round(self._calculate_error_rate(), 2),
            "latency_p95_1h": round(self._calculate_latency_p95(), 2),
            "mttd_minutes": round(self._calculate_mttd(), 2),
            "mttr_minutes": round(self._calculate_mttr(), 2),
            "incident_count_30d": self._count_incidents(),
        }
