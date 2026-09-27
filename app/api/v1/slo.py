"""SLO/SLI API endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database.connection import get_db
from app.database.repositories import (
    create_slo_definition,
    get_slo_definition,
    get_slo_measurements,
    list_slo_definitions,
)
from app.slo.calculator import SLOCalculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/slo", tags=["SLO/SLI"])


# ── Schemas ────────────────────────────────────────────────────────────


class SLOCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    metric_name: str = Field(..., min_length=1)
    target_value: float
    window: str = "30d"
    description: str | None = None
    severity_if_breaking: str = "HIGH"


# ── Endpoints ──────────────────────────────────────────────────────────


@router.get("/definitions")
def list_slo_definitions_endpoint(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all SLO definitions."""
    return list_slo_definitions(db, include_disabled=True)


@router.post("/definitions", status_code=status.HTTP_201_CREATED)
def create_slo(
    request: SLOCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Create a new SLO definition."""
    slo = create_slo_definition(
        db,
        name=request.name,
        metric_name=request.metric_name,
        target_value=request.target_value,
        window=request.window,
        description=request.description,
        severity_if_breaking=request.severity_if_breaking,
    )
    return slo


@router.post("/evaluate")
def evaluate_slos(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Trigger SLO evaluation for all definitions."""
    calculator = SLOCalculator(db)
    results = calculator.evaluate_all()
    return {"results": results, "count": len(results)}


@router.get("/summary")
def get_sre_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get SRE metrics summary."""
    calculator = SLOCalculator(db)
    return calculator.get_sre_summary()


@router.get("/measurements/{slo_id}")
def get_slo_measurements_endpoint(
    slo_id: int,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get measurements for a specific SLO."""
    slo = get_slo_definition(db, slo_id)
    if not slo:
        raise HTTPException(status_code=404, detail="SLO not found")
    return get_slo_measurements(db, slo_id, limit=limit)
