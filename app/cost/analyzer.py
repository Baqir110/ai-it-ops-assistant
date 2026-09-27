"""Infrastructure cost optimization analyzer.

Analyzes resource utilization and generates rightsizing recommendations.
Uses a provider abstraction so AWS/GCP/Azure can be added later.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.database.models import Service
from app.database.repositories import (
    get_recent_checks,
    list_cost_recommendations,
    save_cost_recommendation,
)
from app.monitoring.metrics import COST_RECOMMENDATIONS

logger = logging.getLogger(__name__)


@dataclass
class CostRecommendation:
    resource_name: str
    resource_type: str
    current_request: float | None
    observed_average: float | None
    recommendation: str
    category: str
    potential_savings: str | None = None  # Only if pricing data available


class CostProvider(ABC):
    """Abstract cost data provider."""

    @abstractmethod
    def get_resource_utilization(self, resource_name: str) -> dict:
        """Return utilization data for a resource."""
        ...

    @abstractmethod
    def get_pricing(self, resource_type: str) -> float | None:
        """Return unit pricing if available."""
        ...


class LocalCostProvider(CostProvider):
    """Local provider using Prometheus metrics and service metadata."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_resource_utilization(self, resource_name: str) -> dict:
        from app.database.repositories import get_service_by_name

        service = get_service_by_name(self._db, resource_name)
        if not service:
            return {}

        checks = get_recent_checks(self._db, service.id, limit=100)
        if not checks:
            return {}

        latencies = [c.latency_ms for c in checks if c.latency_ms]
        return {
            "service_name": service.name,
            "check_count": len(checks),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "availability": sum(1 for c in checks if c.available) / len(checks) * 100,
            "metadata": service.metadata_ or {},
        }

    def get_pricing(self, resource_type: str) -> float | None:
        # No pricing data available locally
        return None


class CostAnalyzer:
    """Analyzes infrastructure and generates cost recommendations."""

    def __init__(self, db: Session, provider: CostProvider | None = None) -> None:
        self._db = db
        self._provider = provider or LocalCostProvider(db)

    def analyze(self) -> list[CostRecommendation]:
        """Run cost analysis and generate recommendations."""
        recommendations: list[CostRecommendation] = []

        # Analyze all services
        from app.database.repositories import list_services

        services = list_services(self._db, include_disabled=True)

        for service in services:
            recs = self._analyze_service(service)
            recommendations.extend(recs)

        # Persist new recommendations
        for rec in recommendations:
            existing = list_cost_recommendations(self._db, limit=100)
            # Don't duplicate recent recommendations
            already_exists = any(
                e.resource_name == rec.resource_name
                and e.recommendation == rec.recommendation
                for e in existing
            )
            if not already_exists:
                save_cost_recommendation(
                    self._db,
                    resource_name=rec.resource_name,
                    resource_type=rec.resource_type,
                    recommendation=rec.recommendation,
                    current_request=rec.current_request,
                    observed_average=rec.observed_average,
                    category=rec.category,
                    environment=service.environment,
                )
                COST_RECOMMENDATIONS.labels(category=rec.category).inc()

        return recommendations

    def _analyze_service(self, service: Service) -> list[CostRecommendation]:
        """Analyze a single service for cost optimization."""
        recommendations: list[CostRecommendation] = []

        utilization = self._provider.get_resource_utilization(service.name)
        if not utilization:
            return recommendations

        metadata = utilization.get("metadata", {})

        # Check for CPU rightsizing opportunity
        cpu_request = metadata.get("cpu_request_millicores")
        cpu_avg = metadata.get("cpu_avg_millicores")

        if cpu_request and cpu_avg and cpu_request > 0:
            utilization_ratio = cpu_avg / cpu_request
            if utilization_ratio < 0.25:
                # Using less than 25% of requested CPU
                recommended = max(int(cpu_avg * 2), 100)  # 2x headroom, min 100m
                recommendations.append(
                    CostRecommendation(
                        resource_name=service.name,
                        resource_type="kubernetes_deployment",
                        current_request=float(cpu_request),
                        observed_average=float(cpu_avg),
                        recommendation=(
                            f"Reduce CPU request from {cpu_request}m to ~{recommended}m. "
                            f"Observed average: {cpu_avg}m ({utilization_ratio:.0%} utilization)."
                        ),
                        category="cpu_rightsizing",
                    )
                )

        # Check for memory rightsizing opportunity
        mem_request = metadata.get("memory_request_mb")
        mem_avg = metadata.get("memory_avg_mb")

        if mem_request and mem_avg and mem_request > 0:
            utilization_ratio = mem_avg / mem_request
            if utilization_ratio < 0.25:
                recommended = max(int(mem_avg * 2), 128)  # 2x headroom, min 128MB
                recommendations.append(
                    CostRecommendation(
                        resource_name=service.name,
                        resource_type="kubernetes_deployment",
                        current_request=float(mem_request),
                        observed_average=float(mem_avg),
                        recommendation=(
                            f"Reduce memory request from {mem_request}MB to ~{recommended}MB. "
                            f"Observed average: {mem_avg}MB ({utilization_ratio:.0%} utilization)."
                        ),
                        category="memory_rightsizing",
                    )
                )

        # Check for idle services
        availability = utilization.get("availability", 100)
        check_count = utilization.get("check_count", 0)
        if check_count > 10 and availability == 100:
            avg_latency = utilization.get("avg_latency_ms", 0)
            if avg_latency < 10:  # Very low latency = likely idle
                recommendations.append(
                    CostRecommendation(
                        resource_name=service.name,
                        resource_type="service",
                        current_request=None,
                        observed_average=None,
                        recommendation=(
                            f"Service {service.name} appears idle "
                            f"(100% availability, {avg_latency:.1f}ms avg latency). "
                            "Consider if this service is still needed."
                        ),
                        category="idle_service",
                    )
                )

        return recommendations
