from fastapi import APIRouter, HTTPException, status
from app.models.schemas import SystemTelemetry, IncidentReport
from app.services.synthesizer import IncidentSynthesizer

router = APIRouter()
synthesizer = IncidentSynthesizer()

@router.post(
    "/telemetry/analyze",
    response_model=IncidentReport,
    status_code=status.HTTP_200_OK,
    summary="Analyze system telemetry and generate incident report",
    description="Accepts CPU, RAM, Disk, service, and HTTP endpoint metrics, evaluates anomalies against thresholds, queries runbooks, and returns structured incident analysis."
)
async def analyze_telemetry(telemetry: SystemTelemetry) -> IncidentReport:
    try:
        report = synthesizer.analyze_telemetry(telemetry)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process telemetry payload: {str(e)}"
        )

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy", "service": "AI IT Operations Assistant"}