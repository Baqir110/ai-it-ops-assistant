"""Initial OpsGuard schema.

Revision ID: 0001
Revises:
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Services
    op.create_table(
        "services",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("kind", sa.String(50), nullable=False, server_default="application"),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column(
            "environment", sa.String(50), nullable=False, server_default="production"
        ),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "health_status", sa.String(20), nullable=False, server_default="unknown"
        ),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "consecutive_failures", sa.Integer, nullable=False, server_default="0"
        ),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_services_name", "services", ["name"], unique=True)

    # Service checks
    op.create_table(
        "service_checks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "service_id",
            sa.Integer,
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("available", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_service_checks_service_id", "service_checks", ["service_id"])
    op.create_index("ix_service_checks_checked_at", "service_checks", ["checked_at"])

    # Incidents
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("incident_key", sa.String(30), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DETECTED"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column(
            "affected_service_id",
            sa.Integer,
            sa.ForeignKey("services.id"),
            nullable=True,
        ),
        sa.Column(
            "environment", sa.String(50), nullable=False, server_default="production"
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration", sa.Float, nullable=True),
        sa.Column("symptoms", sa.Text, nullable=True),
        sa.Column("probable_root_cause", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("recommended_remediation", sa.Text, nullable=True),
        sa.Column(
            "remediation_status", sa.String(30), nullable=True, server_default="pending"
        ),
        sa.Column("remediation_result", sa.Text, nullable=True),
        sa.Column(
            "detection_event_id",
            sa.Integer,
            sa.ForeignKey("detection_events.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_incidents_incident_key", "incidents", ["incident_key"], unique=True
    )
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_detected_at", "incidents", ["detected_at"])

    # Detection events
    op.create_table(
        "detection_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("service", sa.String(255), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("value", sa.Float, nullable=True),
        sa.Column("threshold", sa.Float, nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column(
            "environment", sa.String(50), nullable=False, server_default="production"
        ),
        sa.Column(
            "incident_id", sa.Integer, sa.ForeignKey("incidents.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_detection_events_source", "detection_events", ["source"])
    op.create_index(
        "ix_detection_events_event_type", "detection_events", ["event_type"]
    )
    op.create_index(
        "ix_detection_events_created_at", "detection_events", ["created_at"]
    )

    # Incident events
    op.create_table(
        "incident_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "incident_id",
            sa.Integer,
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_incident_events_incident_id", "incident_events", ["incident_id"]
    )
    op.create_index("ix_incident_events_created_at", "incident_events", ["created_at"])

    # Incident evidence
    op.create_table(
        "incident_evidence",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "incident_id",
            sa.Integer,
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("metadata", sa.JSON, nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_incident_evidence_incident_id", "incident_evidence", ["incident_id"]
    )
    op.create_index(
        "ix_incident_evidence_collected_at", "incident_evidence", ["collected_at"]
    )

    # Diagnoses
    op.create_table(
        "diagnoses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "incident_id",
            sa.Integer,
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("probable_cause", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0"),
        sa.Column("alternative_causes", sa.JSON, nullable=True),
        sa.Column("evidence_summary", sa.Text, nullable=True),
        sa.Column("recommended_action", sa.Text, nullable=True),
        sa.Column("runbook_key", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_diagnoses_incident_id", "diagnoses", ["incident_id"])
    op.create_index("ix_diagnoses_created_at", "diagnoses", ["created_at"])

    # Remediation actions
    op.create_table(
        "remediation_actions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "incident_id",
            sa.Integer,
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="LOW"),
        sa.Column(
            "approval_required", sa.Boolean, nullable=False, server_default=sa.true()
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("requested_by", sa.String(100), nullable=True),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.String(20), nullable=True),
        sa.Column("output", sa.Text, nullable=True),
        sa.Column(
            "rollback_capable", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "rollback_executed", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column("rollback_result", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_remediation_actions_incident_id", "remediation_actions", ["incident_id"]
    )

    # Remediation executions
    op.create_table(
        "remediation_executions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "action_id",
            sa.Integer,
            sa.ForeignKey("remediation_actions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("executed_by", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("output", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_remediation_executions_action_id", "remediation_executions", ["action_id"]
    )
    op.create_index(
        "ix_remediation_executions_started_at", "remediation_executions", ["started_at"]
    )

    # SLO definitions
    op.create_table(
        "slo_definitions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("target_value", sa.Float, nullable=False),
        sa.Column("window", sa.String(50), nullable=False, server_default="30d"),
        sa.Column(
            "severity_if_breaking", sa.String(20), nullable=False, server_default="HIGH"
        ),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_slo_definitions_name", "slo_definitions", ["name"], unique=True)

    # SLO measurements
    op.create_table(
        "slo_measurements",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "slo_id", sa.Integer, sa.ForeignKey("slo_definitions.id"), nullable=False
        ),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_value", sa.Float, nullable=False),
        sa.Column("within_target", sa.Boolean, nullable=False),
    )
    op.create_index("ix_slo_measurements_slo_id", "slo_measurements", ["slo_id"])
    op.create_index(
        "ix_slo_measurements_measured_at", "slo_measurements", ["measured_at"]
    )

    # Runbooks
    op.create_table(
        "runbooks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("symptoms", sa.Text, nullable=True),
        sa.Column("evidence_to_collect", sa.JSON, nullable=True),
        sa.Column("diagnosis", sa.Text, nullable=True),
        sa.Column("safe_actions", sa.JSON, nullable=True),
        sa.Column("risky_actions", sa.JSON, nullable=True),
        sa.Column("rollback_instructions", sa.Text, nullable=True),
        sa.Column("verification_steps", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_runbooks_key", "runbooks", ["key"], unique=True)

    # Audit logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "incident_id", sa.Integer, sa.ForeignKey("incidents.id"), nullable=True
        ),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("performed_by", sa.String(100), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_audit_logs_incident_id", "audit_logs", ["incident_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    # Cost recommendations
    op.create_table(
        "cost_recommendations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("resource_name", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("current_request", sa.Float, nullable=True),
        sa.Column("observed_average", sa.Float, nullable=True),
        sa.Column("recommendation", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column(
            "environment", sa.String(50), nullable=False, server_default="production"
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_cost_recommendations_created_at", "cost_recommendations", ["created_at"]
    )


def downgrade() -> None:
    op.drop_table("cost_recommendations")
    op.drop_table("audit_logs")
    op.drop_table("runbooks")
    op.drop_table("slo_measurements")
    op.drop_table("slo_definitions")
    op.drop_table("remediation_executions")
    op.drop_table("remediation_actions")
    op.drop_table("diagnoses")
    op.drop_table("incident_evidence")
    op.drop_table("incident_events")
    op.drop_table("detection_events")
    op.drop_table("incidents")
    op.drop_table("service_checks")
    op.drop_table("services")
    op.drop_table("users")
