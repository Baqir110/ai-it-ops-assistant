"""Cost optimization API endpoints."""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.cost.analyzer import CostAnalyzer
from app.database.connection import get_db
from app.database.repositories import list_cost_recommendations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cost", tags=["Cost Optimization"])


@router.get("/recommendations")
def get_cost_recommendations(
    status_filter: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get cost optimization recommendations."""
    return list_cost_recommendations(db, status=status_filter, limit=limit)


@router.post("/analyze", status_code=status.HTTP_200_OK)
def run_cost_analysis(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Trigger a cost analysis run."""
    analyzer = CostAnalyzer(db)
    recommendations = analyzer.analyze()
    return {
        "recommendations_count": len(recommendations),
        "recommendations": [
            {
                "resource_name": r.resource_name,
                "resource_type": r.resource_type,
                "recommendation": r.recommendation,
                "category": r.category,
            }
            for r in recommendations
        ],
    }
