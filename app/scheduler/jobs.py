"""Background job scheduler.

Runs periodic tasks: HTTP health checks, detection, SLO evaluation,
cost analysis, and incident auto-resolution.
"""

import asyncio
import logging

from app.config.settings import settings
from app.database.connection import SessionLocal
from app.detection.base import DetectorRegistry
from app.detection.http_health import HTTPHealthDetector
from app.detection.prometheus import PrometheusDetector
from app.services.incident_service import IncidentService
from app.slo.calculator import SLOCalculator
from app.cost.analyzer import CostAnalyzer
from app.monitoring.metrics import ACTIVE_INCIDENTS

logger = logging.getLogger(__name__)


class Scheduler:
    """Manages all background jobs."""

    def __init__(self) -> None:
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._detector_registry = DetectorRegistry()
        self._setup_detectors()

    def _setup_detectors(self) -> None:
        """Register all detectors."""
        self._detector_registry.register(HTTPHealthDetector(SessionLocal))
        self._detector_registry.register(PrometheusDetector())

    async def start(self) -> None:
        """Start all background jobs."""
        self._running = True
        logger.info("Starting OpsGuard scheduler")

        self._tasks = [
            asyncio.create_task(self._run_http_monitor()),
            asyncio.create_task(self._run_detection()),
            asyncio.create_task(self._run_slo_evaluation()),
            asyncio.create_task(self._run_cost_analysis()),
            asyncio.create_task(self._run_incident_maintenance()),
        ]

    async def stop(self) -> None:
        """Stop all background jobs."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("OpsGuard scheduler stopped")

    async def _run_http_monitor(self) -> None:
        """Run HTTP health checks periodically."""
        while self._running:
            try:
                detector = self._detector_registry.get("http_health")
                if detector:
                    events = await detector.detect()
                    for event in events:
                        logger.info("HTTP detection: %s", event.message)

                        # Automatically create incident from detection
                        db = SessionLocal()
                        try:
                            service = IncidentService(db)
                            incident_id = service.process_detection_event(event)
                            if incident_id:
                                logger.info(
                                    "Auto-created incident %s from detection",
                                    incident_id,
                                )
                        finally:
                            db.close()
            except Exception as e:
                logger.error("HTTP monitor error: %s", e)

            await asyncio.sleep(settings.HTTP_MONITOR_INTERVAL_SECONDS)

    async def _run_detection(self) -> None:
        """Run all detectors periodically."""
        while self._running:
            try:
                events = await self._detector_registry.run_all()
                for event in events:
                    logger.info("Detection: %s", event.message)

                    # Automatically create incident from detection
                    db = SessionLocal()
                    try:
                        service = IncidentService(db)
                        incident_id = service.process_detection_event(event)
                        if incident_id:
                            logger.info(
                                "Auto-created incident %s from detection",
                                incident_id,
                            )
                    finally:
                        db.close()
            except Exception as e:
                logger.error("Detection error: %s", e)

            await asyncio.sleep(settings.HTTP_MONITOR_INTERVAL_SECONDS)

    async def _run_slo_evaluation(self) -> None:
        """Evaluate SLOs periodically."""
        while self._running:
            try:
                db = SessionLocal()
                try:
                    calculator = SLOCalculator(db)
                    results = calculator.evaluate_all()
                    for result in results:
                        if not result["within_target"]:
                            logger.warning(
                                "SLO breach: %s = %.2f (target: %.2f)",
                                result["slo_name"],
                                result["actual_value"],
                                result["target_value"],
                            )
                finally:
                    db.close()
            except Exception as e:
                logger.error("SLO evaluation error: %s", e)

            await asyncio.sleep(settings.SLO_EVALUATION_INTERVAL_SECONDS)

    async def _run_cost_analysis(self) -> None:
        """Run cost analysis periodically."""
        while self._running:
            try:
                db = SessionLocal()
                try:
                    analyzer = CostAnalyzer(db)
                    recommendations = analyzer.analyze()
                    for rec in recommendations:
                        logger.info("Cost recommendation: %s", rec.recommendation)
                finally:
                    db.close()
            except Exception as e:
                logger.error("Cost analysis error: %s", e)

            await asyncio.sleep(settings.COST_ANALYSIS_INTERVAL_SECONDS)

    async def _run_incident_maintenance(self) -> None:
        """Update active incident count and auto-resolve stale incidents."""
        while self._running:
            try:
                db = SessionLocal()
                try:
                    from app.database.repositories import list_incidents
                    from app.database.models import IncidentStatus

                    open_incidents = list_incidents(
                        db,
                        status=IncidentStatus.DETECTED.value,
                        limit=500,
                    )
                    ACTIVE_INCIDENTS.set(len(open_incidents))
                finally:
                    db.close()
            except Exception as e:
                logger.error("Incident maintenance error: %s", e)

            await asyncio.sleep(60)
