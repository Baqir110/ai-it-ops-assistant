"""Database package — imports all models so create_all sees them."""

from app.database.connection import Base, SessionLocal, engine, get_db

# Import all models so they register with Base.metadata
from app.database.models import (  # noqa: F401
    AuditLogEntry,
    CostRecommendation,
    DetectionEvent,
    Diagnosis,
    Incident,
    IncidentEvent,
    IncidentEvidence,
    RemediationAction,
    RemediationExecution,
    Runbook,
    SLOMeasurement,
    SLODefinition,
    Service,
    ServiceCheck,
    User,
)

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "User",
    "Service",
    "ServiceCheck",
    "Incident",
    "DetectionEvent",
    "IncidentEvent",
    "IncidentEvidence",
    "Diagnosis",
    "RemediationAction",
    "RemediationExecution",
    "SLODefinition",
    "SLOMeasurement",
    "Runbook",
    "AuditLogEntry",
    "CostRecommendation",
]
