"""
Planner Guardrail

Runs after the Planner Agent (which already applies its own internal
guardrails in agents/planner.py::_enforce_guardrails). This is an
independent, defense-in-depth check using the canonical action vocabulary
from guardrails/config.py, so it still catches issues even if planner.py's
own logic is bypassed, disabled, or changes in the future.

Reads/writes state["planned_emails"]: list[PlannedEmail]. Actions live at
`item.action_plan.actions` (a real, declared, mutable field — safe to
reassign). Everything else (review status, etc.) goes into
state["guardrail_flags"], since PlannedEmail has no such fields declared.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from state import EmailWorkflowState

from .base import BaseGuardrail, planned_email_id, set_guardrail_flags
from .config import GuardrailConfig
from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


class PlannerGuard(BaseGuardrail):

    name = "PlannerGuard"

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        planned = state.get("planned_emails", [])

        review_required = []
        modified = False
        new_state = deepcopy(state)
        new_planned = []

        for item in planned:
            email_id = planned_email_id(item)
            actions = list(dict.fromkeys(item.action_plan.actions))  # dedupe, preserve order

            # Empty action list -> default to do_nothing
            if not actions:
                actions = ["do_nothing"]
                modified = True

            # Cap action count
            if len(actions) > GuardrailConfig.MAX_ACTIONS_PER_EMAIL:
                actions = actions[: GuardrailConfig.MAX_ACTIONS_PER_EMAIL]
                modified = True

            # Strip unrecognized actions
            valid_actions = []
            for action in actions:
                if action in GuardrailConfig.ALLOWED_ACTIONS:
                    valid_actions.append(action)
                else:
                    logger.warning("Invalid planner action: %s", action)
                    modified = True
            actions = valid_actions

            # do_nothing must be exclusive
            if "do_nothing" in actions and len(actions) > 1:
                actions = ["do_nothing"]
                modified = True

            # human_approval, if present, must be last (drafted actions run first)
            if "human_approval" in actions:
                actions = [a for a in actions if a != "human_approval"] + ["human_approval"]

            # Does this email need human approval before any tool executes?
            approval_needed = any(a in GuardrailConfig.HUMAN_APPROVAL_ACTIONS for a in actions)
            if approval_needed:
                review_required.append(email_id)

            item.action_plan.actions = actions  # safe: real declared field
            new_planned.append(item)

            set_guardrail_flags(
                new_state,
                email_id,
                planner_guard_status="review_required" if approval_needed else "approved",
                requires_human_approval=approval_needed,
            )

        new_state["planned_emails"] = new_planned

        if review_required:
            decision = GuardDecision.REVIEW
            reason = "Planner produced actions requiring human approval."
        elif modified:
            decision = GuardDecision.MODIFY
            reason = "Planner output normalized."
        else:
            decision = GuardDecision.ALLOW
            reason = "Planner output validated."

        return GuardResult(
            decision=decision,
            passed=True,
            updated_state=new_state,
            reason=reason,
            metadata={"review_required": review_required, "modified": modified},
            guardrail_name=self.name,
        )
