"""
Tool Permission Guardrail

Validates whether each planned action is allowed to actually invoke a tool.
Runs immediately before ToolArgumentGuard / Executor, per workflow.txt.

For any action requiring approval (see GuardrailConfig.TOOL_REGISTRY), this
guard checks state["guardrail_flags"][email_id]["human_approved"] — set
externally once a human has reviewed the email (e.g. via an API endpoint
that flips this flag and re-runs the graph from this node). Unapproved
high-stakes actions are stripped from the plan rather than executed.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from state import EmailWorkflowState

from .base import BaseGuardrail, get_guardrail_flag, planned_email_id, set_guardrail_flags
from .config import GuardrailConfig
from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


class ToolPermissionGuard(BaseGuardrail):

    name = "ToolPermissionGuard"

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        planned = state.get("planned_emails", [])

        review_required = []
        blocked = []
        modified = False
        new_state = deepcopy(state)
        new_planned = []

        for item in planned:
            email_id = planned_email_id(item)
            human_approved = get_guardrail_flag(state, email_id, "human_approved", False)

            approved_actions = []
            for action in item.action_plan.actions:
                # "human_approval" is a control marker, not a real tool call — pass through.
                if action == "human_approval":
                    approved_actions.append(action)
                    continue

                tool = GuardrailConfig.TOOL_REGISTRY.get(action)

                if tool is None:
                    logger.warning("Unknown tool: %s", action)
                    blocked.append(email_id)
                    continue

                if not tool["enabled"]:
                    logger.warning("Disabled tool: %s", action)
                    blocked.append(email_id)
                    continue

                if GuardrailConfig.READ_ONLY_MODE and not tool["read_only"]:
                    logger.warning("Blocked by read-only mode: %s", action)
                    blocked.append(email_id)
                    continue

                if tool["requires_approval"] and not human_approved:
                    review_required.append(email_id)
                    continue  # strip from plan until approved

                approved_actions.append(action)

            if approved_actions != item.action_plan.actions:
                modified = True

            item.action_plan.actions = approved_actions  # safe: real declared field
            new_planned.append(item)

            set_guardrail_flags(
                new_state,
                email_id,
                tool_permission_status=(
                    "blocked" if email_id in blocked
                    else "review_required" if email_id in review_required
                    else "approved"
                ),
            )

        new_state["planned_emails"] = new_planned

        if blocked:
            decision = GuardDecision.BLOCK
            reason = "One or more tool executions were blocked."
        elif review_required:
            decision = GuardDecision.REVIEW
            reason = "Human approval required before these actions can run."
        elif modified:
            decision = GuardDecision.MODIFY
            reason = "Tool permissions updated the execution plan."
        else:
            decision = GuardDecision.ALLOW
            reason = "All tool permissions validated."

        return GuardResult(
            decision=decision,
            passed=True,
            updated_state=new_state,
            reason=reason,
            metadata={"blocked": blocked, "review_required": review_required},
            guardrail_name=self.name,
        )
