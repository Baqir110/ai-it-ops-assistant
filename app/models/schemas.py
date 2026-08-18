from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnalysisMethod(str, Enum):
    OPENAI = "OPENAI"
    RULE_BASED = "RULE_BASED"


class SystemTelemetry(BaseModel):
    cpu_percent: float = Field(
        ..., ge=0.0, le=100.0, json_schema_extra={"example": 94.0}
    )
    ram_percent: float = Field(
        ..., ge=0.0, le=100.0, json_schema_extra={"example": 91.0}
    )
    disk_percent: float = Field(
        ..., ge=0.0, le=100.0, json_schema_extra={"example": 97.0}
    )
    services: Dict[str, str] = Field(
        ..., json_schema_extra={"example": {"apache2": "DOWN", "postgresql": "UP"}}
    )
    http_endpoints: Dict[str, int] = Field(
        default_factory=dict,
        json_schema_extra={"example": {"https://api.internal/health": 503}},
    )


class RunbookSource(BaseModel):
    title: str
    file_path: str
    relevance_score: float


class IncidentReport(BaseModel):
    incident_title: str
    severity: SeverityLevel
    likely_cause: str
    recommended_actions: List[str]
    escalation_required: bool
    escalation_criteria: Optional[str] = None
    sources_consulted: List[RunbookSource] = []
    analysis_method: AnalysisMethod = AnalysisMethod.RULE_BASED
