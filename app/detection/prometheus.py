"""Prometheus-based detector.

Queries Prometheus for infrastructure metrics and emits detection
events when thresholds are breached.
"""

import logging

import httpx

from app.config.settings import settings
from app.detection.base import Detector, DetectionEvent
from app.domain.severity import SeverityLevel
from app.monitoring.metrics import PROMETHEUS_DETECTIONS

logger = logging.getLogger(__name__)


class PrometheusDetector(Detector):
    """Detects infrastructure issues by querying Prometheus metrics."""

    name = "prometheus"

    def __init__(self) -> None:
        self._url = settings.PROMETHEUS_URL.rstrip("/")
        self._enabled = settings.PROMETHEUS_ENABLED

    async def health_check(self) -> bool:
        if not self._enabled:
            return True
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._url}/-/healthy")
                return resp.status_code == 200
        except Exception:
            return False

    async def detect(self) -> list[DetectionEvent]:
        if not self._enabled:
            return []

        events: list[DetectionEvent] = []

        queries = [
            ("cpu_high", self._cpu_query(), settings.CPU_THRESHOLD, "percent"),
            ("memory_high", self._memory_query(), settings.RAM_THRESHOLD, "percent"),
            ("disk_high", self._disk_query(), settings.DISK_THRESHOLD, "percent"),
            (
                "http_error_rate",
                self._error_rate_query(),
                settings.HTTP_ERROR_RATE_THRESHOLD,
                "percent",
            ),
            (
                "http_latency_p95",
                self._latency_query(),
                settings.HTTP_LATENCY_P95_THRESHOLD_MS,
                "ms",
            ),
        ]

        async with httpx.AsyncClient(
            timeout=settings.PROMETHEUS_QUERY_TIMEOUT
        ) as client:
            for event_type, query, threshold, unit in queries:
                try:
                    results = await self._query(client, query)
                    for result in results:
                        value = float(result["value"][1])
                        if value >= threshold:
                            event = DetectionEvent(
                                source="prometheus",
                                type=event_type,
                                severity=SeverityLevel.HIGH.value,
                                message=(
                                    f"{event_type}: {value:.1f}{unit} "
                                    f"(threshold: {threshold}{unit})"
                                ),
                                service=result.get("metric", {}).get("service"),
                                value=value,
                                threshold=threshold,
                                metadata={
                                    "unit": unit,
                                    "metric": result.get("metric", {}),
                                },
                            )
                            events.append(event)
                            PROMETHEUS_DETECTIONS.labels(type=event_type).inc()
                except Exception as e:
                    logger.warning("Prometheus query failed for %s: %s", event_type, e)

        return events

    async def _query(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Execute a PromQL instant query and return results."""
        resp = await client.get(
            f"{self._url}/api/v1/query",
            params={"query": query},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            return []
        return data.get("data", {}).get("result", [])

    @staticmethod
    def _cpu_query() -> str:
        return (
            "100 - avg by (service) ("
            "rate(node_cpu_seconds_total{mode='idle'}[5m]) * 100"
            ")"
        )

    @staticmethod
    def _memory_query() -> str:
        return (
            "100 * (1 - ("
            "node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes"
            "))"
        )

    @staticmethod
    def _disk_query() -> str:
        return (
            "100 * (1 - ("
            "node_filesystem_avail_bytes{mountpoint='/'} / "
            "node_filesystem_size_bytes{mountpoint='/'}"
            "))"
        )

    @staticmethod
    def _error_rate_query() -> str:
        return (
            "100 * sum by (service) ("
            "rate(http_requests_total{status=~'5..'}[5m])"
            ") / sum by (service) ("
            "rate(http_requests_total[5m])"
            ")"
        )

    @staticmethod
    def _latency_query() -> str:
        return (
            "histogram_quantile(0.95, sum by (le, service) ("
            "rate(http_request_duration_seconds_bucket[5m])"
            ")) * 1000"
        )
