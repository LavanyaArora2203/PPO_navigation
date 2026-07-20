"""
guardrails/

Sequenced per workflow.txt:

    InputGuard -> PromptInjectionGuard -> [Email Understanding] -> [Classifier]
    -> ConfidenceGuard -> [Priority] -> [Planner] -> PlannerGuard
    -> (human approval branch) -> ToolPermissionGuard -> ToolArgumentGuard
    -> [Executor] -> PIIGuard -> OutputGuard -> AuditGuard -> [Memory Guard]

All guards import their action vocabulary from `config.GuardrailConfig`
rather than hardcoding it, and record cross-cutting flags in
`state["guardrail_flags"][email_id]` rather than mutating undeclared fields
on the Pydantic models (see base.py for why).
"""

from .audit_guard import AuditGuard
from .base import BaseGuardrail
from .confidence_guard import ConfidenceGuard
from .config import GuardrailConfig
from .exceptions import (
    GuardrailException,
    InputValidationError,
    InvalidToolArguments,
    OutputValidationError,
    PermissionDenied,
    PlannerViolation,
    PromptInjectionDetected,
    SensitiveDataDetected,
    SpamDetected,
)
from .input_guard import InputGuard
from .output_guard import OutputGuard
from .pii_guard import PIIGuard
from .planner_guard import PlannerGuard
from .prompt_injection_guard import PromptInjectionGuard
from .result import GuardDecision, GuardResult
from .tool_argument_guard import ToolArgumentGuard
from .tool_permission_guard import ToolPermissionGuard

__all__ = [
    "AuditGuard",
    "BaseGuardrail",
    "ConfidenceGuard",
    "GuardrailConfig",
    "GuardrailException",
    "InputValidationError",
    "InvalidToolArguments",
    "OutputValidationError",
    "PermissionDenied",
    "PlannerViolation",
    "PromptInjectionDetected",
    "SensitiveDataDetected",
    "SpamDetected",
    "InputGuard",
    "OutputGuard",
    "PIIGuard",
    "PlannerGuard",
    "PromptInjectionGuard",
    "GuardDecision",
    "GuardResult",
    "ToolArgumentGuard",
    "ToolPermissionGuard",
]
