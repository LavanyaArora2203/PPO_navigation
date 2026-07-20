"""
PII Guardrail

Scans generated outbound content for sensitive information after the
Executor runs. Executor only produces drafted text on `pending_send.body`
(for reply/forward actions awaiting approval) — there is no
`generated_content` field anywhere in the models, so that's what this scans.
Actions with no drafted text (archive, delete, create_task, etc.) have
nothing to scan and are skipped.
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy

from state import EmailWorkflowState

from .base import BaseGuardrail, executed_email_id, set_guardrail_flags
from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


class PIIGuard(BaseGuardrail):

    name = "PIIGuard"

    PATTERNS = {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "PHONE": r"\b(?:\+91[- ]?)?[6-9]\d{9}\b",
        "AADHAAR": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",
        "AWS_KEY": r"AKIA[0-9A-Z]{16}",
        "JWT": r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+\.[A-Za-z0-9._-]+",
        "PASSWORD": r"password\s*[:=]\s*\S+",
        "OTP": r"\bOTP\b.*?\b\d{4,8}\b",
    }

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        executed = state.get("executed_emails", [])

        flagged = []
        new_state = deepcopy(state)

        for item in executed:
            if item.pending_send is None:
                continue  # nothing generated for this email — skip

            email_id = executed_email_id(item)
            findings = self._scan(item.pending_send.body)

            if findings:
                flagged.append(email_id)
                item.requires_human_approval = True  # safe: real declared field
                set_guardrail_flags(new_state, email_id, pii_findings=findings)

        new_state["executed_emails"] = executed

        decision = GuardDecision.REVIEW if flagged else GuardDecision.ALLOW
        reason = "Sensitive information detected." if flagged else "No sensitive information detected."

        return GuardResult(
            decision=decision,
            passed=True,
            updated_state=new_state,
            reason=reason,
            metadata={"flagged": flagged},
            guardrail_name=self.name,
        )

    def _scan(self, text: str) -> list[dict]:
        findings = []
        if not text:
            return findings

        for name, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            for match in matches:
                findings.append({"type": name, "value": match})
                logger.warning("Detected %s", name)

        return findings
