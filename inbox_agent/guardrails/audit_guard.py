"""
Audit Guard

Records every workflow decision. Never blocks execution — always ALLOW.
Runs after OutputGuard, as the last guard before Memory Guard.
"""

from __future__ import annotations

from copy import deepcopy

from audit.logger import AuditLogger
from state import EmailWorkflowState

from .base import BaseGuardrail, executed_email_id, get_guardrail_flag
from .result import GuardDecision, GuardResult


class AuditGuard(BaseGuardrail):

    name = "AuditGuard"

    def __init__(self):
        self.logger = AuditLogger()

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        executed = state.get("executed_emails", [])

        for item in executed:
            email_id = executed_email_id(item)

            self.logger.log(
                workflow="Inbox Management",
                email_id=email_id,
                stage="Execution",
                component="Executor",
                decision="ALLOW",
                status="SUCCESS",
                metadata={
                    "actions": item.planned_email.action_plan.actions,
                    "requires_human_approval": item.requires_human_approval,
                    "pii_findings": get_guardrail_flag(state, email_id, "pii_findings", []),
                    "output_issues": get_guardrail_flag(state, email_id, "output_issues", []),
                },
            )

        return GuardResult(
            decision=GuardDecision.ALLOW,
            passed=True,
            updated_state=deepcopy(state),
            reason="Audit completed.",
            metadata={"records": len(self.logger.records)},
            guardrail_name=self.name,
        )
