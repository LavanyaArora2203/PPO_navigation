"""
Tool Argument Guardrail

Validates that each remaining planned action actually has the data it needs
to execute, before the Executor runs. Runs immediately after
ToolPermissionGuard.

NOTE on "forward": the recipient isn't chosen until a human approves the
send (see executor.py::_draft_forward, which sets `to=""` deliberately).
So this guard can only confirm the email itself is forwardable here — the
actual recipient gets validated again at approval time in the executor.
"""

from __future__ import annotations

import logging
from copy import deepcopy

from state import EmailWorkflowState

from .base import BaseGuardrail, planned_email_id, set_guardrail_flags
from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


class ToolArgumentGuard(BaseGuardrail):

    name = "ToolArgumentGuard"

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        planned = state.get("planned_emails", [])

        blocked = []
        modified = False
        new_state = deepcopy(state)
        new_planned = []

        for item in planned:
            email_id = planned_email_id(item)
            email_info = item.prioritized_email.classified_email.email_info

            valid_actions = []
            for action in item.action_plan.actions:
                validator = getattr(self, f"_validate_{action}", None)

                if validator is None:
                    logger.warning("No validator for action '%s'", action)
                    blocked.append(email_id)
                    continue

                ok, reason = validator(email_info)
                if ok:
                    valid_actions.append(action)
                else:
                    logger.warning("%s failed for %s: %s", action, email_id, reason)
                    blocked.append(email_id)

            if valid_actions != item.action_plan.actions:
                modified = True

            item.action_plan.actions = valid_actions  # safe: real declared field
            new_planned.append(item)

            set_guardrail_flags(
                new_state,
                email_id,
                tool_argument_status="blocked" if email_id in blocked else "approved",
            )

        new_state["planned_emails"] = new_planned

        if blocked:
            decision = GuardDecision.BLOCK
            reason = "Invalid or missing tool arguments."
        elif modified:
            decision = GuardDecision.MODIFY
            reason = "Actions with invalid arguments were removed."
        else:
            decision = GuardDecision.ALLOW
            reason = "All arguments valid."

        return GuardResult(
            decision=decision,
            passed=True,
            updated_state=new_state,
            reason=reason,
            metadata={"blocked": blocked},
            guardrail_name=self.name,
        )

    # ---------------------------------------------------
    # Per-action validators — each takes the EmailInfo
    # ---------------------------------------------------

    def _validate_reply(self, email_info):
        if not email_info.sender.email:
            return False, "Missing sender email to reply to"
        return True, ""

    def _validate_archive(self, email_info):
        return bool(email_info.email_id), "Missing email_id"

    def _validate_delete(self, email_info):
        return bool(email_info.email_id), "Missing email_id"

    def _validate_mark_read(self, email_info):
        return bool(email_info.email_id), "Missing email_id"

    def _validate_flag(self, email_info):
        return bool(email_info.email_id), "Missing email_id"

    def _validate_forward(self, email_info):
        # Recipient is chosen at approval time, not here — see module docstring.
        return bool(email_info.email_id), "Missing email_id"

    def _validate_create_task(self, email_info):
        if not email_info.subject:
            return False, "Missing subject for task title"
        return True, ""

    def _validate_schedule_meeting(self, email_info):
        if not email_info.mentioned_dates_times:
            return False, "No date/time mentioned to schedule against"
        return True, ""

    def _validate_notify_slack(self, email_info):
        if not email_info.subject:
            return False, "Missing subject for Slack message"
        return True, ""

    def _validate_do_nothing(self, email_info):
        return True, ""

    def _validate_human_approval(self, email_info):
        return True, ""
