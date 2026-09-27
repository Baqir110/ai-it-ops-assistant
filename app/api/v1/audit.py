"""Audit log API endpoints."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.connection import get_db
from app.database.repositories import list_audit_logs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("")
def get_audit_logs(
    incident_id: int | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get audit log entries."""
    return list_audit_logs(db, incident_id=incident_id, limit=limit)
