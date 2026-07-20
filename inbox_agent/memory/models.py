from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import MemoryCategory, MemoryType


class MemoryRecord(BaseModel):
    """Single memory stored for a user."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    memory_type: MemoryType
    category: MemoryCategory
    key: str
    value: Any
    confidence: float = 1.0
    source: str = "agent"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)
