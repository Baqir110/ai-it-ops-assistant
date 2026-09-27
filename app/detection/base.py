"""Detector abstraction and standardized detection events."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DetectionEvent:
    """Standardized event produced by any detector.

    This is the universal format that all detectors emit, regardless of
    their data source (Prometheus, HTTP health checks, Kubernetes, etc.).
    """

    source: str
    type: str
    severity: str
    message: str
    service: str | None = None
    value: float | None = None
    threshold: float | None = None
    environment: str = "production"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "type": self.type,
            "severity": self.severity,
            "message": self.message,
            "service": self.service,
            "value": self.value,
            "threshold": self.threshold,
            "environment": self.environment,
            "metadata": self.metadata,
        }


class Detector(ABC):
    """Base class for all detectors.

    A detector is responsible for monitoring one aspect of the
    infrastructure and emitting standardized DetectionEvent objects.
    """

    name: str = "base"

    @abstractmethod
    async def detect(self) -> list[DetectionEvent]:
        """Run detection and return any events found."""
        ...

    async def health_check(self) -> bool:
        """Return True if the detector itself is healthy."""
        return True


class DetectorRegistry:
    """Registry that manages all active detectors."""

    def __init__(self) -> None:
        self._detectors: dict[str, Detector] = {}

    def register(self, detector: Detector) -> None:
        self._detectors[detector.name] = detector

    def unregister(self, name: str) -> None:
        self._detectors.pop(name, None)

    def get(self, name: str) -> Detector | None:
        return self._detectors.get(name)

    def list_detectors(self) -> list[str]:
        return list(self._detectors.keys())

    async def run_all(self) -> list[DetectionEvent]:
        """Run all registered detectors and collect events."""
        all_events: list[DetectionEvent] = []
        for detector in self._detectors.values():
            try:
                events = await detector.detect()
                all_events.extend(events)
            except Exception:
                # Detectors must never crash the scheduler.
                continue
        return all_events
