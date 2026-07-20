"""
Confidence Guardrail

Runs after the Classification Agent. Prevents low-confidence classifications
from reaching Priority/Planner/Executor without review.

Reads state["classified_emails"]: list[ClassifiedEmail], where confidence
lives at `item.classification.confidence` and the email id at
`item.email_info.email_id` — NOT flat `.confidence` / `.id` as in the
original draft.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from state import EmailWorkflowState

from .base import BaseGuardrail, classified_email_id, set_guardrail_flags
from .config import GuardrailConfig
from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


class ConfidenceGuard(BaseGuardrail):

    name = "ConfidenceGuard"

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        classified = state.get("classified_emails", [])

        review_list = []
        blocked_list = []
        new_state = deepcopy(state)

        for item in classified:
            email_id = classified_email_id(item)
            confidence = item.classification.confidence

            if confidence >= GuardrailConfig.HIGH_CONFIDENCE:
                status = "approved"

            elif confidence >= GuardrailConfig.REVIEW_CONFIDENCE:
                status = "approved_with_warning"
                review_list.append(email_id)

            elif confidence >= GuardrailConfig.BLOCK_CONFIDENCE:
                status = "review_required"
                review_list.append(email_id)

            else:
                status = "blocked"
                blocked_list.append(email_id)

            set_guardrail_flags(
                new_state, email_id, confidence_status=status, confidence_score=confidence
            )

        if blocked_list:
            decision = GuardDecision.BLOCK
            reason = "One or more emails have critically low confidence."
        elif review_list:
            decision = GuardDecision.REVIEW
            reason = "Some emails require human review."
        else:
            decision = GuardDecision.ALLOW
            reason = "All classifications have acceptable confidence."

        return GuardResult(
            decision=decision,
            passed=True,
            updated_state=new_state,
            reason=reason,
            metadata={
                "review_count": len(review_list),
                "blocked_count": len(blocked_list),
                "review_emails": review_list,
                "blocked_emails": blocked_list,
            },
            guardrail_name=self.name,
        )
