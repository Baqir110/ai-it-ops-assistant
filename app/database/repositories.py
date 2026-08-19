from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.models import Incident
from app.models.schemas import IncidentReport, SystemTelemetry


def save_incident(
    db: Session, telemetry: SystemTelemetry, report: IncidentReport, anomaly_count: int
):
    incident = Incident(
        title=report.incident_title,
        severity=report.severity.value,
        likely_cause=report.likely_cause,
        anomaly_count=anomaly_count,
        cpu_percent=telemetry.cpu_percent,
        ram_percent=telemetry.ram_percent,
        disk_percent=telemetry.disk_percent,
        source_count=len(report.sources_consulted),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def list_incidents(db: Session, limit: int = 100):
    limit = max(1, min(limit, 500))
    return db.scalars(
        select(Incident).order_by(Incident.created_at.desc()).limit(limit)
    ).all()
