"""
Output Guardrail

Validates AI-generated content before it is sent to users. Runs after
PIIGuard. Like PIIGuard, this scans `pending_send.body` — the only place
drafted outbound text actually lives — and skips emails with no drafted
content.
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy

from state import EmailWorkflowState

from .base import BaseGuardrail, executed_email_id, set_guardrail_flags
from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


class OutputGuard(BaseGuardrail):

    name = "OutputGuard"

    MAX_LENGTH = 5000
    MIN_LENGTH = 20

    PLACEHOLDER_PATTERN = re.compile(r"\[.*?\]|\{\{.*?\}\}", re.IGNORECASE)

    PROFANITY = {"idiot", "stupid", "dumb"}

    REQUIRED_SIGNATURE = False

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        executed = state.get("executed_emails", [])

        flagged = []
        new_state = deepcopy(state)

        for item in executed:
            if item.pending_send is None:
                continue

            email_id = executed_email_id(item)
            content = item.pending_send.body

            issues = []
            issues.extend(self._validate_length(content))
            issues.extend(self._validate_placeholders(content))
            issues.extend(self._validate_profanity(content))
            issues.extend(self._validate_repetition(content))
            issues.extend(self._validate_signature(content))

            if issues:
                flagged.append(email_id)
                item.requires_human_approval = True  # safe: real declared field
                set_guardrail_flags(new_state, email_id, output_issues=issues)

        new_state["executed_emails"] = executed

        decision = GuardDecision.REVIEW if flagged else GuardDecision.ALLOW
        reason = "Output validation failed." if flagged else "Output validated."

        return GuardResult(
            decision=decision,
            passed=True,
            updated_state=new_state,
            reason=reason,
            metadata={"flagged": flagged},
            guardrail_name=self.name,
        )

    # ----------------------------------------
    # Validators
    # ----------------------------------------

    def _validate_length(self, text):
        issues = []
        if len(text) < self.MIN_LENGTH:
            issues.append("Response too short.")
        if len(text) > self.MAX_LENGTH:
            issues.append("Response too long.")
        return issues

    def _validate_placeholders(self, text):
        if self.PLACEHOLDER_PATTERN.search(text):
            return ["Placeholder detected."]
        return []

    def _validate_profanity(self, text):
        words = {w.lower() for w in re.findall(r"\w+", text)}
        bad = words.intersection(self.PROFANITY)
        if bad:
            return [f"Profanity detected: {', '.join(sorted(bad))}"]
        return []

    def _validate_repetition(self, text):
        if len(text.split()) < 10:
            return []
        words = text.lower().split()
        repeated = max(words.count(w) for w in set(words))
        if repeated > 20:
            return ["Excessive repetition."]
        return []

    def _validate_signature(self, text):
        if not self.REQUIRED_SIGNATURE:
            return []
        if "Regards" not in text and "Thanks" not in text:
            return ["Missing signature."]
        return []
