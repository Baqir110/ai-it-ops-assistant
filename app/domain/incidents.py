"""Incident lifecycle state machine and domain logic."""

from app.database.models import IncidentStatus

# Valid state transitions for the incident lifecycle.
# DETECTED → INVESTIGATING → DIAGNOSED → ACTION_REQUIRED → REMEDIATING → VERIFYING → RESOLVED → CLOSED
# FAILED can transition back to ACTION_REQUIRED or INVESTIGATING.
VALID_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.DETECTED: {
        IncidentStatus.INVESTIGATING,
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.INVESTIGATING: {
        IncidentStatus.DIAGNOSED,
        IncidentStatus.ACTION_REQUIRED,
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.DIAGNOSED: {
        IncidentStatus.ACTION_REQUIRED,
        IncidentStatus.REMEDIATING,
        IncidentStatus.RESOLVED,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.ACTION_REQUIRED: {
        IncidentStatus.REMEDIATING,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.REMEDIATING: {
        IncidentStatus.VERIFYING,
        IncidentStatus.FAILED,
    },
    IncidentStatus.VERIFYING: {
        IncidentStatus.RESOLVED,
        IncidentStatus.FAILED,
    },
    IncidentStatus.FAILED: {
        IncidentStatus.ACTION_REQUIRED,
        IncidentStatus.INVESTIGATING,
        IncidentStatus.CLOSED,
    },
    IncidentStatus.RESOLVED: {
        IncidentStatus.CLOSED,
    },
    IncidentStatus.CLOSED: set(),
}

TERMINAL_STATES = {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}
OPEN_STATES = set(IncidentStatus) - TERMINAL_STATES


def can_transition(from_status: IncidentStatus | str, to_status: IncidentStatus | str) -> bool:
    """Check if a state transition is valid."""
    if isinstance(from_status, str):
        from_status = IncidentStatus(from_status)
    if isinstance(to_status, str):
        to_status = IncidentStatus(to_status)
    return to_status in VALID_TRANSITIONS.get(from_status, set())


def transition(
    from_status: IncidentStatus | str,
    to_status: IncidentStatus | str,
) -> IncidentStatus:
    """Validate and return the target status."""
    if isinstance(from_status, str):
        from_status = IncidentStatus(from_status)
    if isinstance(to_status, str):
        to_status = IncidentStatus(to_status)
    if not can_transition(from_status, to_status):
        raise ValueError(
            f"Invalid incident transition: {from_status.value} → {to_status.value}"
        )
    return to_status


def is_open(status: IncidentStatus | str) -> bool:
    if isinstance(status, str):
        status = IncidentStatus(status)
    return status in OPEN_STATES
