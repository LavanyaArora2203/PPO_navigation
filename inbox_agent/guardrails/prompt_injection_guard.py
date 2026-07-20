"""
Prompt Injection Guardrail

Protects every LLM in the workflow by flagging emails whose content tries to
manipulate agent behavior. Runs on state["raw_emails"]: list[dict], right
after InputGuard and before the Email Understanding Agent.
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy

from state import EmailWorkflowState

from .base import BaseGuardrail
from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


class PromptInjectionGuard(BaseGuardrail):

    name = "PromptInjectionGuard"

    DANGEROUS_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"forget\s+your\s+instructions",
        r"forget\s+everything",
        r"system\s+prompt",
        r"developer\s+message",
        r"developer\s+instructions",
        r"assistant\s+instructions",
        r"you\s+are\s+now",
        r"reveal\s+your",
        r"show\s+your\s+prompt",
        r"repeat\s+your\s+prompt",
        r"print\s+your\s+instructions",
        r"execute\s+code",
        r"run\s+python",
        r"call\s+tool",
        r"use\s+tool",
        r"delete\s+all",
        r"override",
        r"bypass",
        r"ignore\s+safety",
        r"disable\s+guard",
    ]

    def preprocess(self, state: EmailWorkflowState) -> EmailWorkflowState:
        return deepcopy(state)

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        emails = state.get("raw_emails", [])
        suspicious = []

        for email in emails:
            score = self._scan_email(email)
            email["prompt_injection_score"] = score
            if score > 0:
                suspicious.append(email["id"])

        new_state = deepcopy(state)
        new_state["raw_emails"] = emails

        return GuardResult(
            decision=GuardDecision.REVIEW if suspicious else GuardDecision.ALLOW,
            passed=True,
            updated_state=new_state,
            metadata={"flagged_emails": suspicious, "count": len(suspicious)},
            reason=(
                "Potential prompt injection detected."
                if suspicious
                else "No prompt injection detected."
            ),
            guardrail_name=self.name,
        )

    def _scan_email(self, email: dict) -> int:
        body = email.get("body", "").lower()
        subject = email.get("subject", "").lower()
        text = subject + "\n" + body

        score = 0
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, text):
                score += 1
                logger.warning("Prompt injection pattern matched: %s", pattern)

        return score
