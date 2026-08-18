from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class TelemetryPayload(BaseModel):
  service_name: str = Field(..., examples=["web-server-01"])
  metric_type: str = Field(..., examples=["cpu_usage"])
  metric_value: float = Field(..., examples=[94.5])
  threshold: float = Field(default=85.0, examples=[80.0])
  status: str = Field(default="ok", examples=["critical"])
  timestamp: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc)
  )
  metadata: Optional[Dict[str, Any]] = None