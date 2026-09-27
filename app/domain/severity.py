"""Severity calculation and comparison utilities."""

from app.database.models import SeverityLevel

SEVERITY_ORDER = [
    SeverityLevel.INFO,
    SeverityLevel.LOW,
    SeverityLevel.MEDIUM,
    SeverityLevel.HIGH,
    SeverityLevel.CRITICAL,
]

SEVERITY_WEIGHTS = {
    SeverityLevel.INFO: 1,
    SeverityLevel.LOW: 2,
    SeverityLevel.MEDIUM: 3,
    SeverityLevel.HIGH: 4,
    SeverityLevel.CRITICAL: 5,
}


def max_severity(a: SeverityLevel | str, b: SeverityLevel | str) -> SeverityLevel:
    """Return the more severe of two severity levels."""
    if isinstance(a, str):
        a = SeverityLevel(a)
    if isinstance(b, str):
        b = SeverityLevel(b)
    return a if SEVERITY_WEIGHTS[a] >= SEVERITY_WEIGHTS[b] else b


def severity_from_value(
    value: float,
    threshold: float,
    critical_multiplier: float = 1.15,
) -> SeverityLevel:
    """Derive severity from a metric value relative to its threshold."""
    if value >= threshold * critical_multiplier:
        return SeverityLevel.CRITICAL
    if value >= threshold:
        return SeverityLevel.HIGH
    if value >= threshold * 0.85:
        return SeverityLevel.MEDIUM
    return SeverityLevel.LOW
