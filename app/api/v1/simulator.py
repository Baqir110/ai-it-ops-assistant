"""Failure simulator — DEVELOPMENT ONLY.

This module provides endpoints to safely simulate infrastructure
failures for testing and demonstration purposes. It is ONLY active
when FAILURE_SIMULATOR_ENABLED=true (never in production).
"""

import asyncio
import logging
import random

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.config.settings import settings
from app.database.connection import get_db
from app.database.repositories import (
    get_service_by_name,
    list_services,
    save_service_check,
    update_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulator", tags=["Failure Simulator (Dev Only)"])

# Track active simulations
_active_simulations: dict[str, asyncio.Task] = {}


class SimulationRequest(BaseModel):
    simulation_type: str  # http_500, latency_spike, cpu_spike, memory_pressure, container_crash, bad_deployment, failed_backup
    duration_seconds: int = 60
    target_service: str | None = None


def _check_enabled():
    if not settings.FAILURE_SIMULATOR_ENABLED or settings.is_production:
        raise HTTPException(
            status_code=403,
            detail="Failure simulator is disabled in this environment",
        )


@router.post("/trigger")
async def trigger_simulation(
    request: SimulationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Trigger a failure simulation."""
    _check_enabled()

    sim_id = f"{request.simulation_type}_{random.randint(1000, 9999)}"

    if sim_id in _active_simulations:
        raise HTTPException(status_code=409, detail="Simulation already running")

    task = asyncio.create_task(
        _run_simulation(
            sim_id,
            request.simulation_type,
            request.duration_seconds,
            request.target_service,
            db,
        )
    )
    _active_simulations[sim_id] = task

    return {
        "simulation_id": sim_id,
        "type": request.simulation_type,
        "duration_seconds": request.duration_seconds,
        "status": "started",
    }


@router.get("/status")
def get_simulation_status(
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Get status of active simulations."""
    _check_enabled()
    return {
        "active_simulations": list(_active_simulations.keys()),
        "simulator_enabled": settings.FAILURE_SIMULATOR_ENABLED,
    }


@router.post("/stop/{sim_id}")
def stop_simulation(
    sim_id: str,
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    """Stop a running simulation."""
    _check_enabled()
    task = _active_simulations.get(sim_id)
    if task:
        task.cancel()
        del _active_simulations[sim_id]
        return {"status": "stopped", "simulation_id": sim_id}
    raise HTTPException(status_code=404, detail="Simulation not found")


async def _run_simulation(
    sim_id: str,
    sim_type: str,
    duration: int,
    target_service: str | None,
    db: Session,
):
    """Run a failure simulation in the background."""
    logger.warning(
        "Starting failure simulation: %s (duration: %ds)", sim_type, duration
    )

    try:
        if sim_type == "http_500":
            await _simulate_http_500(duration, target_service, db)
        elif sim_type == "latency_spike":
            await _simulate_latency_spike(duration, target_service, db)
        elif sim_type == "cpu_spike":
            await _simulate_cpu_spike(duration)
        elif sim_type == "memory_pressure":
            await _simulate_memory_pressure(duration)
        elif sim_type == "bad_deployment":
            await _simulate_bad_deployment(duration, target_service, db)
        elif sim_type == "failed_backup":
            await _simulate_failed_backup(duration)
        elif sim_type == "container_crash":
            await _simulate_container_crash(duration, target_service, db)
        else:
            logger.warning("Unknown simulation type: %s", sim_type)
    except asyncio.CancelledError:
        logger.info("Simulation %s cancelled", sim_id)
    finally:
        _active_simulations.pop(sim_id, None)
        logger.info("Simulation %s completed", sim_id)


async def _simulate_http_500(duration: int, target_service: str | None, db: Session):
    """Simulate HTTP 500 errors by recording failed health checks."""
    from datetime import datetime, timezone

    end_time = asyncio.get_event_loop().time() + duration
    while asyncio.get_event_loop().time() < end_time:
        services = list_services(db, include_disabled=False)
        for service in services:
            if target_service and service.name != target_service:
                continue
            # Record a failed check
            save_service_check(
                db=db,
                service_id=service.id,
                status_code=500,
                latency_ms=None,
                available=False,
                error="Simulated HTTP 500 error",
            )
            update_service(db, service.id, health_status="unhealthy")
        await asyncio.sleep(5)


async def _simulate_latency_spike(
    duration: int, target_service: str | None, db: Session
):
    """Simulate latency spike by recording high-latency health checks."""
    from datetime import datetime, timezone

    end_time = asyncio.get_event_loop().time() + duration
    while asyncio.get_event_loop().time() < end_time:
        services = list_services(db, include_disabled=False)
        for service in services:
            if target_service and service.name != target_service:
                continue
            # Record a high-latency check
            save_service_check(
                db=db,
                service_id=service.id,
                status_code=200,
                latency_ms=5000.0,  # 5 seconds
                available=True,
            )
        await asyncio.sleep(5)


async def _simulate_cpu_spike(duration: int):
    """Simulate CPU spike by consuming CPU."""
    import time

    end_time = time.monotonic() + duration
    while time.monotonic() < end_time:
        # Busy loop to consume CPU
        _ = sum(i * i for i in range(10000))
        await asyncio.sleep(0.01)


async def _simulate_memory_pressure(duration: int):
    """Simulate memory pressure by allocating memory."""
    chunks = []
    try:
        end_time = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < end_time:
            chunks.append(bytearray(1024 * 1024))  # 1MB chunks
            await asyncio.sleep(1)
    finally:
        chunks.clear()


async def _simulate_bad_deployment(
    duration: int, target_service: str | None, db: Session
):
    """Simulate a bad deployment by recording failed checks and updating service metadata."""
    from datetime import datetime, timezone

    end_time = asyncio.get_event_loop().time() + duration
    while asyncio.get_event_loop().time() < end_time:
        services = list_services(db, include_disabled=False)
        for service in services:
            if target_service and service.name != target_service:
                continue
            # Record multiple failed checks
            for _ in range(3):
                save_service_check(
                    db=db,
                    service_id=service.id,
                    status_code=500,
                    latency_ms=None,
                    available=False,
                    error="Simulated bad deployment",
                )
            update_service(db, service.id, health_status="unhealthy")
        await asyncio.sleep(5)


async def _simulate_failed_backup(duration: int):
    """Simulate a failed backup."""
    await asyncio.sleep(duration)


async def _simulate_container_crash(
    duration: int, target_service: str | None, db: Session
):
    """Simulate container crash by recording failed checks."""
    from datetime import datetime, timezone

    end_time = asyncio.get_event_loop().time() + duration
    while asyncio.get_event_loop().time() < end_time:
        services = list_services(db, include_disabled=False)
        for service in services:
            if target_service and service.name != target_service:
                continue
            save_service_check(
                db=db,
                service_id=service.id,
                status_code=None,
                latency_ms=None,
                available=False,
                error="Simulated container crash",
            )
            update_service(db, service.id, health_status="unhealthy")
        await asyncio.sleep(5)
