from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditRecord(BaseModel):
    timestamp: datetime
    workflow: str
    email_id: str
    stage: str
    component: str
    decision: str
    status: str
    duration_ms: float | None = None
    metadata: dict[str, Any] = {}
    error: str | None = None
