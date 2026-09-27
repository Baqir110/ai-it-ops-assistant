"""Repository layer for OpsGuard.

All database access goes through these functions. API routes and
services never touch the Session directly.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.database.models import (
    AuditLogEntry,
    CostRecommendation,
    DetectionEvent,
    Diagnosis,
    Incident,
    IncidentEvent,
    IncidentEvidence,
    IncidentStatus,
    RemediationAction,
    RemediationExecution,
    Runbook,
    SLOMeasurement,
    SLODefinition,
    Service,
    ServiceCheck,
    User,
)


# ── Users ──────────────────────────────────────────────────────────────


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def create_user(db: Session, username: str, email: str, hashed_password: str, role: str) -> User:
    user = User(username=username, email=email, hashed_password=hashed_password, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, limit: int = 100) -> list[User]:
    return db.scalars(select(User).order_by(User.created_at.desc()).limit(limit)).all()


def update_last_login(db: Session, user: User) -> None:
    user.last_login = datetime.now(timezone.utc)
    db.commit()


# ── Services ───────────────────────────────────────────────────────────


def get_service(db: Session, service_id: int) -> Service | None:
    return db.get(Service, service_id)


def get_service_by_name(db: Session, name: str) -> Service | None:
    return db.execute(select(Service).where(Service.name == name)).scalar_one_or_none()


def list_services(db: Session, include_disabled: bool = False) -> list[Service]:
    stmt = select(Service).order_by(Service.name)
    if not include_disabled:
        stmt = stmt.where(Service.is_enabled.is_(True))
    return db.scalars(stmt).all()


def create_service(
    db: Session,
    name: str,
    display_name: str | None = None,
    kind: str = "application",
    url: str | None = None,
    environment: str = "production",
    tags: dict | None = None,
    metadata: dict | None = None,
) -> Service:
    service = Service(
        name=name,
        display_name=display_name,
        kind=kind,
        url=url,
        environment=environment,
        tags=tags,
        metadata_=metadata,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def update_service(db: Session, service_id: int, **kwargs) -> Service:
    service = db.get(Service, service_id)
    if not service:
        raise ValueError(f"Service {service_id} not found")
    for key, value in kwargs.items():
        if key == "metadata":
            service.metadata_ = value
        else:
            setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service_id: int) -> None:
    service = db.get(Service, service_id)
    if service:
        db.delete(service)
        db.commit()


# ── Service Checks ─────────────────────────────────────────────────────


def save_service_check(
    db: Session,
    service_id: int,
    status_code: int | None,
    latency_ms: float | None,
    available: bool,
    error: str | None = None,
) -> ServiceCheck:
    check = ServiceCheck(
        service_id=service_id,
        status_code=status_code,
        latency_ms=latency_ms,
        available=available,
        error=error,
    )
    db.add(check)

    service = db.get(Service, service_id)
    if service:
        service.last_health_check = datetime.now(timezone.utc)
        service.health_status = "healthy" if available else "unhealthy"
        service.consecutive_failures = 0 if available else service.consecutive_failures + 1

    db.commit()
    db.refresh(check)
    return check


def get_recent_checks(db: Session, service_id: int, limit: int = 50) -> list[ServiceCheck]:
    return db.scalars(
        select(ServiceCheck)
        .where(ServiceCheck.service_id == service_id)
        .order_by(ServiceCheck.checked_at.desc())
        .limit(limit)
    ).all()


def get_service_availability(db: Session, service_id: int, window_minutes: int = 60) -> float:
    """Calculate availability percentage over a time window."""
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    total = db.scalar(
        select(func.count(ServiceCheck.id)).where(
            and_(ServiceCheck.service_id == service_id, ServiceCheck.checked_at >= since)
        )
    )
    if not total:
        return 100.0
    available = db.scalar(
        select(func.count(ServiceCheck.id)).where(
            and_(
                ServiceCheck.service_id == service_id,
                ServiceCheck.checked_at >= since,
                ServiceCheck.available.is_(True),
            )
        )
    )
    return (available / total) * 100.0


# ── Detection Events ───────────────────────────────────────────────────


def save_detection_event(
    db: Session,
    source: str,
    event_type: str,
    severity: str,
    message: str,
    service: str | None = None,
    value: float | None = None,
    threshold: float | None = None,
    environment: str = "production",
) -> DetectionEvent:
    event = DetectionEvent(
        source=source,
        event_type=event_type,
        service=service,
        severity=severity,
        value=value,
        threshold=threshold,
        message=message,
        environment=environment,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_detection_events(
    db: Session,
    limit: int = 100,
    service: str | None = None,
    event_type: str | None = None,
) -> list[DetectionEvent]:
    stmt = select(DetectionEvent).order_by(DetectionEvent.created_at.desc()).limit(limit)
    if service:
        stmt = stmt.where(DetectionEvent.service == service)
    if event_type:
        stmt = stmt.where(DetectionEvent.event_type == event_type)
    return db.scalars(stmt).all()


def find_duplicate_detection(
    db: Session,
    event_type: str,
    service: str | None,
    window_minutes: int = 30,
) -> DetectionEvent | None:
    """Check if a similar detection event already exists within the dedup window."""
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    stmt = select(DetectionEvent).where(
        and_(
            DetectionEvent.event_type == event_type,
            DetectionEvent.created_at >= since,
        )
    )
    if service:
        stmt = stmt.where(DetectionEvent.service == service)
    return db.execute(stmt.order_by(DetectionEvent.created_at.desc())).scalars().first()


# ── Incidents ──────────────────────────────────────────────────────────


def _generate_incident_key(db: Session) -> str:
    """Generate a unique incident key like INC-2026-0001."""
    year = datetime.now(timezone.utc).year
    prefix = f"INC-{year}-"
    latest = db.execute(
        select(Incident.incident_key).where(
            Incident.incident_key.like(f"{prefix}%")
        ).order_by(Incident.incident_key.desc())
    ).scalars().first()
    if latest:
        try:
            seq = int(latest.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def create_incident(
    db: Session,
    title: str,
    severity: str,
    source: str | None = None,
    affected_service_id: int | None = None,
    environment: str = "production",
    description: str | None = None,
    symptoms: str | None = None,
    detection_event_id: int | None = None,
) -> Incident:
    incident = Incident(
        incident_key=_generate_incident_key(db),
        title=title,
        description=description,
        severity=severity,
        status=IncidentStatus.DETECTED.value,
        source=source,
        affected_service_id=affected_service_id,
        environment=environment,
        symptoms=symptoms,
        detection_event_id=detection_event_id,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return db.get(Incident, incident_id)


def get_incident_by_key(db: Session, incident_key: str) -> Incident | None:
    return db.execute(
        select(Incident).where(Incident.incident_key == incident_key)
    ).scalar_one_or_none()


def list_incidents(
    db: Session,
    status: str | None = None,
    severity: str | None = None,
    service_id: int | None = None,
    limit: int = 100,
) -> list[Incident]:
    stmt = select(Incident).order_by(Incident.detected_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Incident.status == status)
    if severity:
        stmt = stmt.where(Incident.severity == severity)
    if service_id:
        stmt = stmt.where(Incident.affected_service_id == service_id)
    return db.scalars(stmt).all()


def update_incident_status(
    db: Session,
    incident_id: int,
    status: str,
) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")
    incident.status = status
    now = datetime.now(timezone.utc)
    if status == IncidentStatus.RESOLVED.value and not incident.resolved_at:
        incident.resolved_at = now
    if status == IncidentStatus.CLOSED.value and not incident.closed_at:
        incident.closed_at = now
    if incident.detected_at and incident.resolved_at:
        incident.duration = (incident.resolved_at - incident.detected_at).total_seconds()
    db.commit()
    db.refresh(incident)
    return incident


def update_incident(
    db: Session,
    incident_id: int,
    **kwargs,
) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")
    for key, value in kwargs.items():
        setattr(incident, key, value)
    db.commit()
    db.refresh(incident)
    return incident


def add_incident_event(
    db: Session,
    incident_id: int,
    event_type: str,
    message: str,
    metadata: dict | None = None,
) -> IncidentEvent:
    event = IncidentEvent(
        incident_id=incident_id,
        event_type=event_type,
        message=message,
        metadata_=metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_incident_events(db: Session, incident_id: int) -> list[IncidentEvent]:
    return db.scalars(
        select(IncidentEvent)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.created_at)
    ).all()


def find_open_incident_for_service(
    db: Session,
    service_id: int,
    event_type: str | None = None,
) -> Incident | None:
    """Find an existing open incident for a service to avoid duplicates."""
    open_statuses = [
        IncidentStatus.DETECTED.value,
        IncidentStatus.INVESTIGATING.value,
        IncidentStatus.DIAGNOSED.value,
        IncidentStatus.ACTION_REQUIRED.value,
        IncidentStatus.REMEDIATING.value,
        IncidentStatus.VERIFYING.value,
    ]
    stmt = select(Incident).where(
        and_(
            Incident.affected_service_id == service_id,
            Incident.status.in_(open_statuses),
        )
    )
    if event_type:
        stmt = stmt.where(Incident.source == event_type)
    return db.execute(stmt.order_by(Incident.detected_at.desc())).scalars().first()


# ── Evidence ───────────────────────────────────────────────────────────


def add_evidence(
    db: Session,
    incident_id: int,
    evidence_type: str,
    source: str,
    content: str,
    metadata: dict | None = None,
) -> IncidentEvidence:
    evidence = IncidentEvidence(
        incident_id=incident_id,
        evidence_type=evidence_type,
        source=source,
        content=content,
        metadata_=metadata,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def get_incident_evidence(db: Session, incident_id: int) -> list[IncidentEvidence]:
    return db.scalars(
        select(IncidentEvidence)
        .where(IncidentEvidence.incident_id == incident_id)
        .order_by(IncidentEvidence.collected_at)
    ).all()


# ── Diagnosis ───────────────────────────────────────────────────────────


def save_diagnosis(
    db: Session,
    incident_id: int,
    probable_cause: str,
    confidence: float,
    alternative_causes: list | None = None,
    evidence_summary: str | None = None,
    recommended_action: str | None = None,
    runbook_key: str | None = None,
) -> Diagnosis:
    diagnosis = Diagnosis(
        incident_id=incident_id,
        probable_cause=probable_cause,
        confidence=confidence,
        alternative_causes=alternative_causes,
        evidence_summary=evidence_summary,
        recommended_action=recommended_action,
        runbook_key=runbook_key,
    )
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


def get_diagnoses(db: Session, incident_id: int) -> list[Diagnosis]:
    return db.scalars(
        select(Diagnosis)
        .where(Diagnosis.incident_id == incident_id)
        .order_by(Diagnosis.created_at.desc())
    ).all()


# ── Remediation ────────────────────────────────────────────────────────


def create_remediation_action(
    db: Session,
    incident_id: int,
    action_type: str,
    risk_level: str,
    approval_required: bool = True,
    requested_by: str | None = None,
    rollback_capable: bool = False,
) -> RemediationAction:
    action = RemediationAction(
        incident_id=incident_id,
        action_type=action_type,
        risk_level=risk_level,
        approval_required=approval_required,
        requested_by=requested_by,
        rollback_capable=rollback_capable,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def get_remediation_action(db: Session, action_id: int) -> RemediationAction | None:
    return db.get(RemediationAction, action_id)


def list_remediation_actions(db: Session, incident_id: int) -> list[RemediationAction]:
    return db.scalars(
        select(RemediationAction)
        .where(RemediationAction.incident_id == incident_id)
        .order_by(RemediationAction.created_at)
    ).all()


def update_remediation_action(db: Session, action_id: int, **kwargs) -> RemediationAction:
    action = db.get(RemediationAction, action_id)
    if not action:
        raise ValueError(f"Remediation action {action_id} not found")
    for key, value in kwargs.items():
        setattr(action, key, value)
    db.commit()
    db.refresh(action)
    return action


def save_remediation_execution(
    db: Session,
    action_id: int,
    result: str,
    executed_by: str | None = None,
    output: str | None = None,
) -> RemediationExecution:
    execution = RemediationExecution(
        action_id=action_id,
        result=result,
        executed_by=executed_by,
        output=output,
        completed_at=datetime.now(timezone.utc),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


# ── SLO ────────────────────────────────────────────────────────────────


def list_slo_definitions(db: Session, include_disabled: bool = False) -> list[SLODefinition]:
    stmt = select(SLODefinition).order_by(SLODefinition.name)
    if not include_disabled:
        stmt = stmt.where(SLODefinition.is_enabled.is_(True))
    return db.scalars(stmt).all()


def get_slo_definition(db: Session, slo_id: int) -> SLODefinition | None:
    return db.get(SLODefinition, slo_id)


def create_slo_definition(
    db: Session,
    name: str,
    metric_name: str,
    target_value: float,
    window: str = "30d",
    description: str | None = None,
    severity_if_breaking: str = "HIGH",
) -> SLODefinition:
    slo = SLODefinition(
        name=name,
        metric_name=metric_name,
        target_value=target_value,
        window=window,
        description=description,
        severity_if_breaking=severity_if_breaking,
    )
    db.add(slo)
    db.commit()
    db.refresh(slo)
    return slo


def save_slo_measurement(
    db: Session,
    slo_id: int,
    actual_value: float,
    within_target: bool,
) -> SLOMeasurement:
    measurement = SLOMeasurement(
        slo_id=slo_id,
        actual_value=actual_value,
        within_target=within_target,
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return measurement


def get_slo_measurements(
    db: Session, slo_id: int, limit: int = 100
) -> list[SLOMeasurement]:
    return db.scalars(
        select(SLOMeasurement)
        .where(SLOMeasurement.slo_id == slo_id)
        .order_by(SLOMeasurement.measured_at.desc())
        .limit(limit)
    ).all()


# ── Runbooks ───────────────────────────────────────────────────────────


def get_runbook_by_key(db: Session, key: str) -> Runbook | None:
    return db.execute(select(Runbook).where(Runbook.key == key)).scalar_one_or_none()


def list_runbooks(db: Session) -> list[Runbook]:
    return db.scalars(select(Runbook).order_by(Runbook.key)).all()


def create_runbook(
    db: Session,
    key: str,
    title: str,
    category: str,
    content: str,
    **kwargs,
) -> Runbook:
    runbook = Runbook(key=key, title=title, category=category, content=content, **kwargs)
    db.add(runbook)
    db.commit()
    db.refresh(runbook)
    return runbook


def update_runbook(db: Session, runbook_id: int, **kwargs) -> Runbook:
    runbook = db.get(Runbook, runbook_id)
    if not runbook:
        raise ValueError(f"Runbook {runbook_id} not found")
    for key, value in kwargs.items():
        setattr(runbook, key, value)
    db.commit()
    db.refresh(runbook)
    return runbook


# ── Audit Log ──────────────────────────────────────────────────────────


def save_audit_log(
    db: Session,
    action: str,
    details: dict | None = None,
    performed_by: str | None = None,
    incident_id: int | None = None,
) -> AuditLogEntry:
    entry = AuditLogEntry(
        action=action,
        details=details,
        performed_by=performed_by,
        incident_id=incident_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_audit_logs(
    db: Session,
    incident_id: int | None = None,
    limit: int = 200,
) -> list[AuditLogEntry]:
    stmt = select(AuditLogEntry).order_by(AuditLogEntry.timestamp.desc()).limit(limit)
    if incident_id:
        stmt = stmt.where(AuditLogEntry.incident_id == incident_id)
    return db.scalars(stmt).all()


# ── Cost Recommendations ───────────────────────────────────────────────


def save_cost_recommendation(
    db: Session,
    resource_name: str,
    resource_type: str,
    recommendation: str,
    current_request: float | None = None,
    observed_average: float | None = None,
    category: str | None = None,
    environment: str = "production",
) -> CostRecommendation:
    rec = CostRecommendation(
        resource_name=resource_name,
        resource_type=resource_type,
        current_request=current_request,
        observed_average=observed_average,
        recommendation=recommendation,
        category=category,
        environment=environment,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def list_cost_recommendations(
    db: Session, status: str | None = None, limit: int = 100
) -> list[CostRecommendation]:
    stmt = select(CostRecommendation).order_by(CostRecommendation.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(CostRecommendation.status == status)
    return db.scalars(stmt).all()
