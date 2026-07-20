"""
Abstract base class for all guardrails, plus shared helpers.

Every guardrail follows the same lifecycle:

run()
    ├── preprocess()
    ├── validate()
    └── postprocess()

Subclasses usually only override validate().

--------------------------------------------------------------------------
Why the helpers below exist
--------------------------------------------------------------------------
The pipeline's Pydantic models are nested (ClassifiedEmail -> EmailInfo,
PlannedEmail -> PrioritizedEmail -> ClassifiedEmail -> EmailInfo, etc.), and
none of them declare fields like `guardrail_status` or `human_approved`.
Setting an undeclared attribute on a Pydantic model raises an error, so
guardrails must NOT do `setattr(item, "some_new_field", ...)` on these
objects. The two exceptions are `action_plan.actions` (a real, declared,
mutable field) and `ExecutedEmail.requires_human_approval` (also declared)
— those two are safe to mutate directly.

For everything else, guardrails record extra info in
`state["guardrail_flags"][email_id]`, a plain dict added alongside the
typed EmailWorkflowState fields. This is intentionally NOT declared in
state.py's TypedDict (TypedDict isn't enforced at runtime), so it works
without editing the agent models or state.py.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from state import EmailWorkflowState

from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Path helpers — the single place that knows how to reach an email_id
# through each stage's nested model shape.
# --------------------------------------------------------------------------


def classified_email_id(item: Any) -> str:
    """email_id for an item in state['classified_emails']."""
    return item.email_info.email_id


def planned_email_id(item: Any) -> str:
    """email_id for an item in state['planned_emails']."""
    return item.prioritized_email.classified_email.email_info.email_id


def executed_email_id(item: Any) -> str:
    """email_id for an item in state['executed_emails']."""
    return item.planned_email.prioritized_email.classified_email.email_info.email_id


# --------------------------------------------------------------------------
# guardrail_flags helpers
# --------------------------------------------------------------------------


def set_guardrail_flags(state: EmailWorkflowState, email_id: str, **flags: Any) -> EmailWorkflowState:
    """Merge `flags` into state['guardrail_flags'][email_id]. Mutates and returns state."""
    state.setdefault("guardrail_flags", {})
    state["guardrail_flags"].setdefault(email_id, {})
    state["guardrail_flags"][email_id].update(flags)
    return state


def get_guardrail_flag(state: EmailWorkflowState, email_id: str, key: str, default: Any = None) -> Any:
    return state.get("guardrail_flags", {}).get(email_id, {}).get(key, default)


# --------------------------------------------------------------------------
# Base guardrail
# --------------------------------------------------------------------------


class BaseGuardrail(ABC):

    name = "BaseGuardrail"

    def run(self, state: EmailWorkflowState) -> GuardResult:
        """Execute the full guardrail lifecycle."""
        logger.info("%s started", self.name)

        state = self.preprocess(state)
        result = self.validate(state)
        result = self.postprocess(result)

        logger.info("%s finished (%s)", self.name, result.decision.value)

        return result

    def __call__(self, state: EmailWorkflowState) -> GuardResult:
        """Allows: guard(state)  instead of  guard.run(state)"""
        return self.run(state)

    def preprocess(self, state: EmailWorkflowState) -> EmailWorkflowState:
        """Optional preprocessing (e.g. normalize sender, trim whitespace)."""
        return state

    @abstractmethod
    def validate(self, state: EmailWorkflowState) -> GuardResult:
        """Core validation logic."""
        raise NotImplementedError

    def postprocess(self, result: GuardResult) -> GuardResult:
        """Optional cleanup (e.g. logging, masking, statistics)."""
        return result
