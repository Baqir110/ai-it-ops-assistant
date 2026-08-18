from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.repositories import list_incidents, save_incident
from app.models.schemas import IncidentReport, SystemTelemetry
from app.monitoring.metrics import (
    ANOMALIES_DETECTED,
    CPU_USAGE,
    DISK_USAGE,
    INCIDENTS_CREATED,
    RAM_USAGE,
    REQUEST_LATENCY,
    TELEMETRY_REQUESTS,
)
from app.services.synthesizer import IncidentSynthesizer


router = APIRouter()
synthesizer = IncidentSynthesizer()


@router.post(
    "/telemetry/analyze",
    response_model=IncidentReport,
    status_code=status.HTTP_200_OK,
    summary="Analyze system telemetry and generate incident report",
    description=(
        "Accepts CPU, RAM, Disk, service, and HTTP endpoint metrics, "
        "evaluates anomalies against thresholds, queries runbooks, "
        "persists the generated incident, and returns structured incident analysis."
    ),
)
async def analyze_telemetry(
    telemetry: SystemTelemetry,
    db: Session = Depends(get_db),
) -> IncidentReport:
    start_time = perf_counter()

    TELEMETRY_REQUESTS.inc()

    CPU_USAGE.set(telemetry.cpu_percent)
    RAM_USAGE.set(telemetry.ram_percent)
    DISK_USAGE.set(telemetry.disk_percent)

    try:
        report = synthesizer.analyze_telemetry(telemetry)

        detection = synthesizer.detector.evaluate(telemetry)
        anomaly_count = detection["anomaly_count"]

        if detection["has_anomalies"]:
            ANOMALIES_DETECTED.inc(anomaly_count)

        save_incident(
            db=db,
            telemetry=telemetry,
            report=report,
            anomaly_count=anomaly_count,
        )

        INCIDENTS_CREATED.labels(
            severity=report.severity.value
        ).inc()

        return report

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process telemetry payload: {str(e)}",
        ) from e

    finally:
        REQUEST_LATENCY.observe(perf_counter() - start_time)


@router.get(
    "/incidents",
    status_code=status.HTTP_200_OK,
    summary="List recent incidents",
)
def get_incidents(
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
):
    return list_incidents(db, limit=limit)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
async def health_check():
    return {
        "status": "healthy",
        "service": "AI IT Operations Assistant",
    }