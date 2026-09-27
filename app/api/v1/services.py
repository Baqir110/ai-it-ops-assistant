"""Service management API endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database.connection import get_db
from app.database.repositories import (
    create_service,
    delete_service,
    get_recent_checks,
    get_service,
    get_service_availability,
    get_service_by_name,
    list_services,
    update_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/services", tags=["Services"])


# ── Schemas ────────────────────────────────────────────────────────────


class ServiceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = None
    kind: str = "application"
    url: str | None = None
    environment: str = "production"
    tags: dict | None = None
    metadata: dict | None = None


class ServiceUpdateRequest(BaseModel):
    display_name: str | None = None
    kind: str | None = None
    url: str | None = None
    environment: str | None = None
    is_enabled: bool | None = None
    tags: dict | None = None
    metadata: dict | None = None


class ServiceResponse(BaseModel):
    id: int
    name: str
    display_name: str | None
    kind: str
    url: str | None
    environment: str
    is_enabled: bool
    health_status: str
    last_health_check: datetime | None
    consecutive_failures: int
    tags: dict | None
    metadata_: dict | None

    class Config:
        from_attributes = True


# ── Endpoints ──────────────────────────────────────────────────────────


@router.get("", response_model=list[ServiceResponse])
def list_all_services(
    include_disabled: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all monitored services."""
    return list_services(db, include_disabled=include_disabled)


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def register_service(
    request: ServiceCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Register a new service for monitoring."""
    existing = get_service_by_name(db, request.name)
    if existing:
        raise HTTPException(status_code=409, detail="Service already exists")

    service = create_service(
        db,
        name=request.name,
        display_name=request.display_name,
        kind=request.kind,
        url=request.url,
        environment=request.environment,
        tags=request.tags,
        metadata=request.metadata,
    )
    return service


@router.get("/{service_id}", response_model=ServiceResponse)
def get_service_detail(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get service details."""
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.patch("/{service_id}", response_model=ServiceResponse)
def update_service_details(
    service_id: int,
    request: ServiceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Update a service."""
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    update_data = request.model_dump(exclude_unset=True)
    updated = update_service(db, service_id, **update_data)
    return updated


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin"])),
):
    """Remove a service from monitoring."""
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    delete_service(db, service_id)


@router.get("/{service_id}/health")
def get_service_health(
    service_id: int,
    window_minutes: int = Query(default=60, ge=1, le=1440),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get current health status for a service."""
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    availability = get_service_availability(db, service_id, window_minutes)
    recent_checks = get_recent_checks(db, service_id, limit=20)

    return {
        "service": service,
        "availability_pct": round(availability, 1),
        "window_minutes": window_minutes,
        "recent_checks": recent_checks,
    }


@router.post("/{service_id}/disable", response_model=ServiceResponse)
def disable_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Disable monitoring for a service."""
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return update_service(db, service_id, is_enabled=False)


@router.post("/{service_id}/enable", response_model=ServiceResponse)
def enable_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Enable monitoring for a service."""
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return update_service(db, service_id, is_enabled=True)
