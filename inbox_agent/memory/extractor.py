from typing import Any

from pydantic import BaseModel

from .enums import MemoryCategory, MemoryType


class MemoryCandidate(BaseModel):
    should_store: bool
    confidence: float
    memory_type: MemoryType
    category: MemoryCategory
    key: str
    value: Any
    reasoning: str
