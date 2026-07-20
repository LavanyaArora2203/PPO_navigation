"""
Common exceptions raised by guardrails.
"""


class GuardrailException(Exception):
    """Base class for all guardrail exceptions."""


class InputValidationError(GuardrailException):
    """Incoming email failed validation."""


class PromptInjectionDetected(GuardrailException):
    """Prompt injection attempt detected."""


class SpamDetected(GuardrailException):
    """Email classified as spam."""


class PlannerViolation(GuardrailException):
    """Planner produced unsafe actions."""


class PermissionDenied(GuardrailException):
    """Tool execution denied."""


class InvalidToolArguments(GuardrailException):
    """Tool arguments invalid."""


class SensitiveDataDetected(GuardrailException):
    """Sensitive information detected."""


class OutputValidationError(GuardrailException):
    """Generated response failed validation."""
