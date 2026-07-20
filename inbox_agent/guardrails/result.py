"""
Common return models used by all guardrails.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GuardDecision(str, Enum):
    """Decision taken by a guardrail."""

    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"
    MODIFY = "modify"


class GuardResult(BaseModel):
    decision: GuardDecision
    passed: bool
    reason: str = "Validation successful."
    updated_state: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float | None = None
    guardrail_name: str | None = None
