from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class IncidentReport(BaseModel):
  incident_id: str = Field(..., examples=["INC-1002"])
  service_name: str
  severity: str = Field(..., examples=["CRITICAL"])
  description: str
  triggered_rules: List[str]
  suggested_runbook: Optional[str] = None
  created_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc)
  )