"""Detection event API endpoints."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.connection import get_db
from app.database.repositories import get_detection_events

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detection", tags=["Detection"])


@router.get("/events")
def list_detection_events(
    service: str | None = None,
    event_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List detection events."""
    return get_detection_events(db, limit=limit, service=service, event_type=event_type)
